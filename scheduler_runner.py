"""
SCHEDULER RUNNER - Jalankan di cloud (GitHub Actions / Railway / Render)
Atau lokal dengan: python scheduler_runner.py
"""
import os
import sys
import time
import asyncio
import requests
from datetime import datetime
from scheduler import DailyScheduler
from core import SmartFormFiller
from config import get_config

# Import database functions
sys.path.insert(0, os.path.dirname(__file__))
from data.init_db import get_connection, init_database
from job_scraper import get_pending_jobs, mark_job_applied


def send_telegram(message: str):
    """Kirim notifikasi Telegram"""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("[TELEGRAM] Token or chat_id not configured")
        return False
    
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        return False


async def run_once():
    """Jalankan satu iterasi auto-apply"""
    scheduler = DailyScheduler()
    
    # Cek apakah boleh apply
    status = scheduler.can_apply()
    
    if not status["can_apply"]:
        print(f"[SKIP] {status['reason']}")
        return {"applied": 0, "reason": status["reason"]}
    
    # Scrape fresh jobs dulu sebelum apply
    print("[SCRAPE] Scraping fresh Web3 jobs...")
    try:
        from job_scraper import (
            scrape_web3jobsradar, scrape_greenhouse_bulk,
            save_jobs_to_db
        )
        # Web3JobsRadar (gratis, no auth)
        fresh_jobs = await scrape_web3jobsradar(query="marketing", remote=True, limit=30)
        saved = save_jobs_to_db(fresh_jobs, source="web3jobsradar")
        print(f"  [OK] {saved} new jobs from Web3JobsRadar")
        
        # Web3 Greenhouse companies
        gh_jobs = await scrape_greenhouse_bulk(limit_per_company=10)
        saved = save_jobs_to_db(gh_jobs, source="web3_greenhouse")
        print(f"  [OK] {saved} new jobs from Web3 Greenhouse")
    except Exception as e:
        print(f"  [WARN] Scrape error (continuing anyway): {e}")
    
    # Get pending jobs dari database
    remaining = status["remaining_today"]
    jobs = get_pending_jobs(remaining)
    
    if not jobs:
        print("[INFO] No pending jobs to apply")
        return {"applied": 0, "reason": "no_pending_jobs"}
    
    print(f"[START] Processing {len(jobs)} jobs (remaining quota: {remaining})")
    
    config = get_config()
    filler = SmartFormFiller(config)
    
    # Cari CV file
    cv_path = config.cv_path or filler._find_cv_file()
    if cv_path:
        print(f"[CV] Using: {cv_path}")
    else:
        print("[CV] No CV file found - will skip file upload fields")
    
    if not await filler.init_browser():
        print("[ERROR] Failed to init browser")
        return {"applied": 0, "reason": "browser_init_failed"}
    
    applied_count = 0
    failed_count = 0
    
    try:
        for i, job in enumerate(jobs, 1):
            # Re-check scheduler status
            check = scheduler.can_apply()
            if not check["can_apply"]:
                print(f"[LIMIT] {check['reason']}")
                break
            
            url = job["url"]
            title = job.get("title", "N/A")
            company = job.get("company", "N/A")
            job_id = job.get("id")
            
            print(f"\n[{i}/{len(jobs)}] {title} at {company}")
            print(f"  URL: {url}")
            
            try:
                # Fill application (tidak dry-run)
                result = await filler.fill_application(url, cv_path=cv_path, dry_run=False)
                
                success = result.get("status") in ("submitted", "submitted_captcha_may_block")
                captcha_stuck = result.get("status") == "captcha_stuck"
                
                # Record to scheduler
                scheduler.record_application(url, result.get("platform", "unknown"), success)
                
                # Record to database
                _save_application_result(job_id, result)
                
                if captcha_stuck:
                    failed_count += 1
                    reason = result.get("captcha_skip_reason", "CAPTCHA timeout")
                    print(f"  [CAPTCHA SKIP] {reason}")
                    if job_id:
                        mark_job_applied(job_id, False)
                    # Kirim notifikasi Telegram
                    skip_msg = f"""*CAPTCHA Blocked - Job Skipped*

Job: {title}
Company: {company}
URL: {url}
Reason: {reason}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                    send_telegram(skip_msg)
                    continue
                elif result.get("status") == "captcha_blocked":
                    print(f"  [CAPTCHA] Blocked by CAPTCHA - skipping")
                    if job_id:
                        mark_job_applied(job_id, False)
                    continue
                elif success:
                    applied_count += 1
                    status_msg = result.get("status", "submitted")
                    print(f"  [OK] {status_msg}!")
                    if job_id:
                        mark_job_applied(job_id, True)
                else:
                    failed_count += 1
                    print(f"  [FAIL] Status: {result.get('status')}")
                    if job_id:
                        mark_job_applied(job_id, False)
                
            except Exception as e:
                failed_count += 1
                print(f"  [ERROR] {e}")
                if job_id:
                    mark_job_applied(job_id, False)
            
            # Delay antar aplikasi
            if i < len(jobs):
                delay = scheduler.get_next_delay()
                print(f"  [WAIT] {delay//60} minutes before next application...")
                await asyncio.sleep(delay)
    
    finally:
        await filler.close_browser()
    
    result = {
        "applied": applied_count,
        "failed": failed_count,
        "total": len(jobs),
    }
    
    print(f"\n[DONE] Applied: {applied_count}, Failed: {failed_count}")
    return result


def _save_application_result(job_id: int, result: dict):
    """Simpan hasil aplikasi ke database"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO applications (job_id, url, platform, status, fields_filled, 
                                     fields_skipped, custom_questions, captcha_detected, dry_run)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            result.get("url", ""),
            result.get("platform", "unknown"),
            result.get("status", "unknown"),
            result.get("fields_filled", 0),
            result.get("fields_skipped", 0),
            result.get("custom_questions", 0),
            1 if result.get("captcha_detected") else 0,
            1 if result.get("dry_run") else 0,
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")


def send_daily_report():
    """Kirim laporan harian via Telegram"""
    scheduler = DailyScheduler()
    stats = scheduler.get_daily_stats()
    
    msg = f"""*Auto-Apply Bot - Daily Report*

Date: {stats['date']}
Applied Today: {stats['applied']}/{stats['max']}
Remaining: {stats['remaining']}
Total All-Time: {stats['total_all_time']}
Success Rate: {stats['success_rate']:.1f}%
"""
    
    send_telegram(msg)
    print(f"[REPORT] Daily report sent")


def main():
    """Main scheduler loop"""
    # Initialize database
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "data", "jobs.db")):
        init_database()
    
    scheduler = DailyScheduler()
    print(scheduler.get_schedule_display())
    
    # Check status
    status = scheduler.can_apply()
    
    if status["can_apply"]:
        print("[START] Running auto-apply...")
        result = asyncio.run(run_once())
        
        # Send Telegram notification
        if result.get("applied", 0) > 0:
            msg = f"""*Auto-Apply Bot*

Applied: {result['applied']}/{result['total']}
Failed: {result.get('failed', 0)}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            send_telegram(msg)
    else:
        print(f"[WAIT] {status['reason']}")
        if status.get("next_available_time"):
            print(f"[NEXT] Available at: {status['next_available_time']}")
    
    # Send daily report at midnight
    now = datetime.utcnow()
    if now.hour == 0 and now.minute < 30:
        send_daily_report()


if __name__ == "__main__":
    main()
