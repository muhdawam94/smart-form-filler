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
from job_scraper import get_pending_jobs, mark_job_applied, reset_failed_jobs


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
        print(f"\n{'='*50}")
        print(f"[SKIP] {status['reason']}")
        print(f"{'='*50}")
        return {"applied": 0, "reason": status["reason"]}
    
    # Scrape fresh jobs dulu sebelum apply
    print(f"\n{'='*50}")
    print("[SCRAPE] Scraping fresh jobs from multiple sources...")
    print(f"{'='*50}")
    try:
        from job_scraper import (
            scrape_web3jobsradar, scrape_greenhouse_bulk,
            scrape_lever_board, scrape_ashby_board, scrape_web3career,
            scrape_web3career_html, scrape_cryptojobslist,
            save_jobs_to_db
        )
        
        total_saved = 0
        
        # 1. Web3JobsRadar - multiple queries (gratis, API lambat)
        for query in ["", "developer", "engineer", "marketing", "community", "business"]:
            try:
                fresh_jobs = await scrape_web3jobsradar(query=query, remote=True, limit=50)
                saved = save_jobs_to_db(fresh_jobs, source="web3jobsradar")
                total_saved += saved
            except Exception as e:
                print(f"  [WARN] Web3JobsRadar query='{query}' error: {e}")
        
        # 2. Web3 Greenhouse companies (verified working slugs)
        try:
            gh_jobs = await scrape_greenhouse_bulk(limit_per_company=10)
            saved = save_jobs_to_db(gh_jobs, source="web3_greenhouse")
            total_saved += saved
            print(f"  [OK] {saved} new jobs from Web3 Greenhouse")
        except Exception as e:
            print(f"  [WARN] Greenhouse bulk error: {e}")
        
        # 3. Web3.career HTML scraping (no token needed)
        try:
            w3c_jobs = await scrape_web3career_html(tag="", remote=True, limit=50)
            saved = save_jobs_to_db(w3c_jobs, source="web3career_html")
            total_saved += saved
        except Exception as e:
            print(f"  [WARN] Web3.career HTML error: {e}")
        
        # 4. Web3.career API (jika ada token)
        if os.getenv("WEB3_CAREER_TOKEN"):
            for tag in ["", "marketing", "engineering", "community"]:
                try:
                    w3c_api_jobs = await scrape_web3career(tag=tag, remote=True, limit=50)
                    saved = save_jobs_to_db(w3c_api_jobs, source="web3career")
                    total_saved += saved
                except Exception as e:
                    print(f"  [WARN] Web3.career API tag='{tag}' error: {e}")
        else:
            print("  [INFO] Web3.career API skipped (no token). Get free token at: https://web3.career/web3-jobs-api")
        
        # 5. CryptoJobsList (no auth)
        try:
            cjl_jobs = await scrape_cryptojobslist(remote=True, limit=50)
            saved = save_jobs_to_db(cjl_jobs, source="cryptojobslist")
            total_saved += saved
        except Exception as e:
            print(f"  [WARN] CryptoJobsList error: {e}")
        
        # 6. Popular Web3 companies via Lever (verified working: binance 286 jobs)
        LEVER_COMPANIES = ["binance", "swissborg"]
        for company in LEVER_COMPANIES:
            try:
                lever_jobs = await scrape_lever_board(company)
                saved = save_jobs_to_db(lever_jobs, source="lever_scraper")
                total_saved += saved
            except Exception as e:
                print(f"  [WARN] Lever {company} error: {e}")
        
        # 7. Web3 companies via Ashby
        ASHBY_COMPANIES = ["parallel", "uniswap", "opensea"]
        for company in ASHBY_COMPANIES:
            try:
                ashby_jobs = await scrape_ashby_board(company)
                saved = save_jobs_to_db(ashby_jobs, source="ashby_scraper")
                total_saved += saved
            except Exception as e:
                print(f"  [WARN] Ashby {company} error: {e}")
        
        print(f"  [TOTAL] {total_saved} new jobs saved from all sources")
    except Exception as e:
        print(f"  [WARN] Scrape error (continuing anyway): {e}")
    
    # Get pending jobs dari database (termasuk failed jobs yang bisa di-retry)
    remaining = status["remaining_today"]
    max_retries = scheduler.config.get("max_retries", 2)
    jobs = get_pending_jobs(remaining, include_failed=True, max_retries=max_retries)
    
    if not jobs:
        print(f"\n{'='*50}")
        print("[INFO] No pending jobs to apply")
        print(f"{'='*50}")
        return {"applied": 0, "reason": "no_pending_jobs"}
    
    print(f"\n{'='*50}")
    print(f"[START] Processing {len(jobs)} jobs (remaining quota: {remaining})")
    print(f"{'='*50}")
    
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
            job_platform = job.get("platform", "unknown")
            
            # Skip jobs from blocked platforms
            skip_platforms = scheduler.config.get("skip_platforms", [])
            if job_platform.lower() in [p.lower() for p in skip_platforms]:
                print(f"  [SKIP] Platform '{job_platform}' is in skip list")
                if job_id:
                    mark_job_applied(job_id, False, max_retries)
                continue
            
            print(f"\n{'-'*50}")
            print(f"[{i}/{len(jobs)}] {title} at {company}")
            print(f"  URL: {url}")
            print(f"  Platform: {job_platform}")
            print(f"{'-'*50}")
            
            try:
                # Fill application (tidak dry-run)
                result = await filler.fill_application(url, cv_path=cv_path, dry_run=False, company=company)
                
                success = result.get("status") == "submitted"
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
                        mark_job_applied(job_id, False, max_retries)
                    # Kirim notifikasi Telegram
                    skip_msg = f"""⚠️ *CAPTCHA BLOCKED - JOB SKIP*
{'='*35}

💼 Job: *{title}*
🏢 Company: *{company}*
🔗 URL: {url}
❌ Reason: *{reason}*
🕐 Time: *{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

{'='*35}
⏳ Akan di-retry di run berikutnya"""
                    send_telegram(skip_msg)
                    continue
                elif result.get("status") == "captcha_blocked":
                    print(f"  [CAPTCHA] Blocked by CAPTCHA - skipping")
                    if job_id:
                        mark_job_applied(job_id, False, max_retries)
                    continue
                elif success:
                    applied_count += 1
                    status_msg = result.get("status", "submitted")
                    print(f"  [OK] {status_msg}!")
                    if job_id:
                        mark_job_applied(job_id, True, max_retries)
                else:
                    failed_count += 1
                    print(f"  [FAIL] Status: {result.get('status')}")
                    if job_id:
                        mark_job_applied(job_id, False, max_retries)
                
            except Exception as e:
                failed_count += 1
                print(f"  [ERROR] {e}")
                if job_id:
                    mark_job_applied(job_id, False, max_retries)
            
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
    
    print(f"\n{'='*50}")
    print(f"[DONE] Applied: {applied_count}, Failed: {failed_count}")
    print(f"{'='*50}")
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
    
    msg = f"""📊 *AUTO-APPLY BOT - LAPORAN HARIAN*
{'='*35}

📅 Tanggal: *{stats['date']}*
📝 Apply Hari Ini: *{stats['applied']}/{stats['max']}*
📋 Sisa Kuota: *{stats['remaining']}*
🏆 Total Semua: *{stats['total_all_time']}*
✅ Success Rate: *{stats['success_rate']:.1f}%*

{'='*35}
🤖 Smart Form Filler"""
    
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
            msg = f"""🤖 *AUTO-APPLY BOT SELESAI*
{'='*35}

📝 Berhasil Apply: *{result['applied']}/{result['total']}*
❌ Gagal: *{result.get('failed', 0)}*
🕐 Waktu: *{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

{'='*35}
✅ Status: Berhasil mengirim lamaran"""
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
