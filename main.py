"""
SMART FORM FILLER - Main Entry Point
Integrasi dengan job bots yang sudah ada
"""
import asyncio
import os
import sys
import json
import argparse
import requests
from datetime import datetime

from config import get_config, FormFillerConfig
from core import SmartFormFiller, PlatformDetector

# Import database functions
sys.path.insert(0, os.path.dirname(__file__))
from data.init_db import get_connection, init_database
from job_scraper import get_pending_jobs, mark_job_applied


async def fill_single_url(url: str, cv_path: str = None, dry_run: bool = False, 
                           headless: bool = False):
    """Fill application form di satu URL"""
    config = get_config()
    config.headless = headless
    
    filler = SmartFormFiller(config)
    
    if not await filler.init_browser():
        print("[ERROR] Failed to initialize browser")
        return
    
    try:
        result = await filler.fill_application(url, cv_path, dry_run)
        print(f"\n[FINAL RESULT]")
        print(json.dumps(result, indent=2))
    finally:
        await filler.close_browser()


async def fill_from_file(file_path: str, cv_path: str = None, dry_run: bool = False,
                          headless: bool = False, limit: int = None):
    """Fill application forms dari file yang berisi list URLs"""
    config = get_config()
    config.headless = headless
    
    # Load URLs
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    if limit:
        urls = urls[:limit]
    
    print(f"[INFO] Found {len(urls)} URLs to process")
    
    filler = SmartFormFiller(config)
    
    if not await filler.init_browser():
        print("[ERROR] Failed to initialize browser")
        return
    
    results = []
    try:
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            result = await filler.fill_application(url, cv_path, dry_run)
            results.append(result)
            
            # Pause between applications
            if i < len(urls):
                print("[PAUSE] Waiting 5-10 seconds before next application...")
                await asyncio.sleep(5)
    
    finally:
        await filler.close_browser()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(results)} applications processed")
    print(f"{'='*60}")
    
    stats = filler.get_stats()
    print(f"  Submitted: {stats['submitted']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Blocked: {stats['blocked']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    
    # Save results
    output_file = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[SAVED] Results saved to {output_file}")
    
    return results


async def batch_fill_from_jobs_db(db_path: str = None, cv_path: str = None,
                                   dry_run: bool = False, headless: bool = False,
                                   limit: int = 10):
    """Fill applications dari database jobs"""
    # Initialize database if needed
    db_file = db_path or os.path.join(os.path.dirname(__file__), "data", "jobs.db")
    if not os.path.exists(db_file):
        init_database()
    
    jobs = get_pending_jobs(limit)
    
    print(f"[INFO] Found {len(jobs)} unapplied jobs in database")
    
    if not jobs:
        print("[INFO] No jobs to apply to")
        print("[TIP] Add jobs with: python job_scraper.py greenhouse <company>")
        print("[TIP] Or import from file: python job_scraper.py import urls.txt")
        return []
    
    config = get_config()
    config.headless = headless
    
    filler = SmartFormFiller(config)
    
    if not await filler.init_browser():
        print("[ERROR] Failed to initialize browser")
        return []
    
    results = []
    try:
        for i, job in enumerate(jobs, 1):
            job_id = job["id"]
            title = job.get("title", "N/A")
            company = job.get("company", "N/A")
            url = job["url"]
            
            print(f"\n[{i}/{len(jobs)}] {title} at {company}")
            print(f"  URL: {url}")
            
            result = await filler.fill_application(url, cv_path, dry_run)
            result["job_id"] = job_id
            result["job_title"] = title
            result["company"] = company
            results.append(result)
            
            # Update database
            success = result["status"] == "submitted"
            mark_job_applied(job_id, success)
            
            # Handle CAPTCHA stuck - skip and notify
            if result.get("status") == "captcha_stuck":
                reason = result.get("captcha_skip_reason", "CAPTCHA timeout")
                print(f"  [CAPTCHA SKIP] {reason}")
                _send_telegram_captcha_skip(title, company, url, reason)
                continue
            
            # Send Telegram notification for each submission
            if not dry_run and success:
                _send_telegram_notification(title, company, url)
            
            # Pause between applications
            if i < len(jobs):
                print("[PAUSE] Waiting 5-10 seconds before next application...")
                await asyncio.sleep(5)
    
    finally:
        await filler.close_browser()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(results)} applications processed")
    print(f"{'='*60}")
    
    stats = filler.get_stats()
    print(f"  Submitted: {stats['submitted']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Blocked: {stats['blocked']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    
    # Send daily summary
    _send_telegram_summary(stats)
    
    # Save results
    output_file = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[SAVED] Results saved to {output_file}")
    
    return results


def _mark_applied(db_path: str, job_id: int):
    """Mark job as applied in database"""
    # Use the new job_scraper function
    from job_scraper import mark_job_applied as _mark
    _mark(job_id, True)


def _send_telegram_notification(title: str, company: str, url: str):
    """Kirim notifikasi Telegram saat berhasil apply"""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        return
    
    msg = f"""*New Application Submitted!*

Job: {title}
Company: {company}
URL: {url}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
    except:
        pass


def _send_telegram_summary(stats: dict):
    """Kirim ringkasan via Telegram"""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        return
    
    msg = f"""*Auto-Apply Summary*

Total: {stats['total']}
Submitted: {stats['submitted']}
Failed: {stats['failed']}
Blocked: {stats['blocked']}
Success Rate: {stats['success_rate']:.1f}%"""
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
    except:
        pass


def _send_telegram_captcha_skip(title: str, company: str, url: str, reason: str):
    """Kirim notifikasi Telegram saat job di-skip karena CAPTCHA"""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        return
    
    msg = f"""*CAPTCHA Blocked - Job Skipped*

Job: {title}
Company: {company}
URL: {url}
Reason: {reason}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
    except:
        pass


def detect_platform(url: str):
    """Deteksi platform dari URL"""
    detector = PlatformDetector()
    platform = detector.detect(url=url)
    strategy = detector.get_form_strategy(platform)
    
    print(f"URL: {url}")
    print(f"Platform: {platform}")
    print(f"Strategy: {json.dumps(strategy, indent=2)}")
    
    return platform, strategy


def show_stats():
    """Tampilkan statistik submissions"""
    config = get_config()
    
    if not os.path.exists(config.submissions_log):
        print("[INFO] No submissions yet")
        return
    
    filler = SmartFormFiller(config)
    stats = filler.get_stats()
    
    print(f"\n{'='*60}")
    print(f"SUBMISSION STATISTICS")
    print(f"{'='*60}")
    print(f"  Total: {stats['total']}")
    print(f"  Submitted: {stats['submitted']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Blocked: {stats['blocked']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    print(f"\n  By Platform:")
    for platform, count in stats['platforms'].items():
        print(f"    {platform}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Smart Form Filler")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Single URL
    single_parser = subparsers.add_parser("fill", help="Fill single application form")
    single_parser.add_argument("url", help="Application URL")
    single_parser.add_argument("--cv", help="CV file path")
    single_parser.add_argument("--dry-run", action="store_true", help="Don't submit")
    single_parser.add_argument("--headless", action="store_true", help="Run headless")
    
    # From file
    file_parser = subparsers.add_parser("fill-file", help="Fill from URL list file")
    file_parser.add_argument("file", help="File containing URLs (one per line)")
    file_parser.add_argument("--cv", help="CV file path")
    file_parser.add_argument("--dry-run", action="store_true", help="Don't submit")
    file_parser.add_argument("--headless", action="store_true", help="Run headless")
    file_parser.add_argument("--limit", type=int, help="Max URLs to process")
    
    # From database
    db_parser = subparsers.add_parser("fill-db", help="Fill from jobs database")
    db_parser.add_argument("--db", default=None, help="Database path (optional)")
    db_parser.add_argument("--cv", help="CV file path")
    db_parser.add_argument("--dry-run", action="store_true", help="Don't submit")
    db_parser.add_argument("--headless", action="store_true", help="Run headless")
    db_parser.add_argument("--limit", type=int, default=10, help="Max jobs to process")
    
    # Detect platform
    detect_parser = subparsers.add_parser("detect", help="Detect platform from URL")
    detect_parser.add_argument("url", help="URL to analyze")
    
    # Stats
    subparsers.add_parser("stats", help="Show submission statistics")
    
    args = parser.parse_args()
    
    if args.command == "fill":
        asyncio.run(fill_single_url(args.url, args.cv, args.dry_run, args.headless))
    
    elif args.command == "fill-file":
        asyncio.run(fill_from_file(args.file, args.cv, args.dry_run, args.headless, args.limit))
    
    elif args.command == "fill-db":
        asyncio.run(batch_fill_from_jobs_db(args.db, args.cv, args.dry_run, args.headless, args.limit))
    
    elif args.command == "detect":
        detect_platform(args.url)
    
    elif args.command == "stats":
        show_stats()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
