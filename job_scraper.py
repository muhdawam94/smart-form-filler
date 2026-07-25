"""
JOB SCRAPER - Scrape job URLs dari berbagai sumber
Support: Greenhouse, Lever, Ashby boards langsung + manual input
"""
import os
import sys
import json
import re
import time
import random
import sqlite3
import asyncio
from datetime import datetime
from urllib.parse import urlparse

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from data.init_db import get_connection, DB_PATH


# =============================================
# GREENHOUSE BOARD SCRAPER
# =============================================
GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards"

async def scrape_greenhouse_board(company_slug: str) -> list:
    """Scrape semua jobs dari Greenhouse board company"""
    import requests
    
    url = f"{GREENHOUSE_API_BASE}/{company_slug}/jobs"
    print(f"[SCRAPE] Greenhouse: {company_slug}")
    
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "title": job.get("title", ""),
                "company": company_slug,
                "url": job.get("absolute_url", ""),
                "platform": "greenhouse",
                "location": job.get("location", {}).get("name", ""),
                "description": job.get("content", "")[:500] if job.get("content") else "",
            })
        
        print(f"  [OK] Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


# =============================================
# LEVER BOARD SCRAPER
# =============================================
async def scrape_lever_board(company_slug: str) -> list:
    """Scrape semua jobs dari Lever board company"""
    import requests
    
    url = f"https://api.lever.co/v0/postings/{company_slug}"
    print(f"[SCRAPE] Lever: {company_slug}")
    
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        jobs = []
        for job in data:
            jobs.append({
                "title": job.get("text", ""),
                "company": company_slug,
                "url": job.get("hostedUrl", ""),
                "platform": "lever",
                "location": job.get("categories", {}).get("location", ""),
                "description": job.get("descriptionPlain", "")[:500] if job.get("descriptionPlain") else "",
            })
        
        print(f"  [OK] Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


# =============================================
# ASHBY BOARD SCRAPER
# =============================================
async def scrape_ashby_board(company_slug: str) -> list:
    """Scrape semua jobs dari Ashby board company"""
    import requests
    
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
    print(f"[SCRAPE] Ashby: {company_slug}")
    
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        jobs = []
        for job in data.get("jobPostings", []):
            jobs.append({
                "title": job.get("title", ""),
                "company": company_slug,
                "url": f"https://jobs.ashbyhq.com/{company_slug}/{job.get('id', '')}",
                "platform": "ashby",
                "location": job.get("locationName", ""),
                "description": job.get("description", "")[:500] if job.get("description") else "",
            })
        
        print(f"  [OK] Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


# =============================================
# GENERIC URL SCRAPER (pakai Playwright)
# =============================================
async def scrape_job_board_url(url: str) -> list:
    """Scrape jobs dari URL job board apapun pakai Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        print("[ERROR] Playwright not installed")
        return []
    
    print(f"[SCRAPE] URL: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Cari semua job links
            links = await page.query_selector_all("a[href]")
            jobs = []
            seen_urls = set()
            
            for link in links:
                href = await link.get_attribute("href")
                text = await link.text_content()
                
                if not href or not text:
                    continue
                
                # Filter job-related links
                text_lower = text.strip().lower()
                if any(kw in text_lower for kw in ["engineer", "developer", "designer", "manager", "analyst", "specialist", "coordinator", "director", "lead", "intern", "junior", "senior", "staff", "principal"]):
                    full_url = href if href.startswith("http") else f"{urlparse(url).scheme}://{urlparse(url).netloc}{href}"
                    
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        platform = detect_platform_from_url(full_url)
                        jobs.append({
                            "title": text.strip(),
                            "company": urlparse(url).netloc.replace("www.", ""),
                            "url": full_url,
                            "platform": platform,
                            "location": "",
                            "description": "",
                        })
            
            print(f"  [OK] Found {len(jobs)} jobs")
            return jobs
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            return []
        finally:
            await browser.close()


def detect_platform_from_url(url: str) -> str:
    """Detect platform dari URL"""
    url_lower = url.lower()
    platforms = {
        "greenhouse": ["greenhouse.io"],
        "lever": ["lever.co"],
        "ashby": ["ashbyhq.com"],
        "workday": ["myworkdayjobs.com", "workday.com"],
        "smartrecruiters": ["smartrecruiters.com"],
        "bamboohr": ["bamboohr.com"],
    }
    
    for platform, patterns in platforms.items():
        for pattern in patterns:
            if pattern in url_lower:
                return platform
    
    return "unknown"


# =============================================
# DATABASE OPERATIONS
# =============================================
def save_jobs_to_db(jobs: list, source: str = "scraper") -> int:
    """Simpan jobs ke database, return jumlah yang berhasil disimpan"""
    conn = get_connection()
    cursor = conn.cursor()
    saved = 0
    
    for job in jobs:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (title, company, url, platform, location, description, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job.get("title", ""),
                job.get("company", ""),
                job.get("url", ""),
                job.get("platform", "unknown"),
                job.get("location", ""),
                job.get("description", ""),
                source,
            ))
            if cursor.rowcount > 0:
                saved += 1
        except Exception as e:
            print(f"  [DB ERROR] {e}")
    
    conn.commit()
    conn.close()
    return saved


def import_urls_from_file(file_path: str) -> int:
    """Import job URLs dari file teks (satu URL per baris)"""
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return 0
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    jobs = []
    for line in lines:
        url = line.strip()
        if url and not url.startswith('#') and url.startswith('http'):
            platform = detect_platform_from_url(url)
            jobs.append({
                "title": "",
                "company": urlparse(url).netloc.replace("www.", ""),
                "url": url,
                "platform": platform,
                "location": "",
                "description": "",
            })
    
    return save_jobs_to_db(jobs, source="file_import")


def get_pending_jobs(limit: int = 10) -> list:
    """Ambil jobs yang belum di-apply, prioritize platform yang bisa di-auto-fill"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Prioritize by platform: Greenhouse (no CAPTCHA) > Ashby > others > Lever (hCaptcha)
    # Also update scores in DB so future queries benefit
    cursor.execute("""
        UPDATE jobs SET score = CASE
            WHEN platform = 'greenhouse' THEN 10
            WHEN platform = 'ashby' THEN 8
            WHEN platform = 'smartrecruiters' THEN 7
            WHEN platform = 'lever' THEN 0
            ELSE 5
        END
        WHERE applied = 0 AND status = 'pending'
    """)
    conn.commit()
    
    cursor.execute("""
        SELECT id, title, company, url, platform, location
        FROM jobs
        WHERE applied = 0 AND status = 'pending'
        ORDER BY score DESC, created_at DESC
        LIMIT ?
    """, (limit,))
    
    jobs = []
    for row in cursor.fetchall():
        jobs.append({
            "id": row[0],
            "title": row[1],
            "company": row[2],
            "url": row[3],
            "platform": row[4],
            "location": row[5],
        })
    
    conn.close()
    return jobs


def mark_job_applied(job_id: int, success: bool):
    """Tandai job sudah di-apply"""
    conn = get_connection()
    cursor = conn.cursor()
    
    status = "applied" if success else "failed"
    cursor.execute("""
        UPDATE jobs
        SET applied = 1, applied_at = ?, status = ?, updated_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), status, datetime.now().isoformat(), job_id))
    
    conn.commit()
    conn.close()


def add_manual_url(url: str, title: str = "", company: str = "") -> bool:
    """Tambah URL lamaran secara manual"""
    platform = detect_platform_from_url(url)
    jobs = [{
        "title": title,
        "company": company or urlparse(url).netloc.replace("www.", ""),
        "url": url,
        "platform": platform,
        "location": "",
        "description": "",
    }]
    saved = save_jobs_to_db(jobs, source="manual")
    return saved > 0


# =============================================
# CLI
# =============================================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Job Scraper untuk Smart Form Filler")
    subparsers = parser.add_subparsers(dest="command")
    
    # Scrape Greenhouse
    gh_parser = subparsers.add_parser("greenhouse", help="Scrape Greenhouse board")
    gh_parser.add_argument("company", help="Company slug (e.g., 'airbnb')")
    
    # Scrape Lever
    lever_parser = subparsers.add_parser("lever", help="Scrape Lever board")
    lever_parser.add_argument("company", help="Company slug")
    
    # Scrape Ashby
    ashby_parser = subparsers.add_parser("ashby", help="Scrape Ashby board")
    ashby_parser.add_argument("company", help="Company slug")
    
    # Scrape URL
    url_parser = subparsers.add_parser("url", help="Scrape job board URL")
    url_parser.add_argument("url", help="Job board URL")
    
    # Import from file
    file_parser = subparsers.add_parser("import", help="Import URLs from file")
    file_parser.add_argument("file", help="File with URLs (one per line)")
    
    # Add manual URL
    add_parser = subparsers.add_parser("add", help="Add URL manually")
    add_parser.add_argument("url", help="Job application URL")
    add_parser.add_argument("--title", default="", help="Job title")
    add_parser.add_argument("--company", default="", help="Company name")
    
    # List pending jobs
    subparsers.add_parser("list", help="List pending jobs")
    
    # Stats
    subparsers.add_parser("stats", help="Show scraper stats")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize DB if needed
    if not os.path.exists(DB_PATH):
        from data.init_db import init_database
        init_database()
    
    if args.command == "greenhouse":
        jobs = asyncio.run(scrape_greenhouse_board(args.company))
        saved = save_jobs_to_db(jobs, source="greenhouse_scraper")
        print(f"\n[RESULT] {saved} new jobs saved to database")
    
    elif args.command == "lever":
        jobs = asyncio.run(scrape_lever_board(args.company))
        saved = save_jobs_to_db(jobs, source="lever_scraper")
        print(f"\n[RESULT] {saved} new jobs saved to database")
    
    elif args.command == "ashby":
        jobs = asyncio.run(scrape_ashby_board(args.company))
        saved = save_jobs_to_db(jobs, source="ashby_scraper")
        print(f"\n[RESULT] {saved} new jobs saved to database")
    
    elif args.command == "url":
        jobs = asyncio.run(scrape_job_board_url(args.url))
        saved = save_jobs_to_db(jobs, source="url_scraper")
        print(f"\n[RESULT] {saved} new jobs saved to database")
    
    elif args.command == "import":
        saved = import_urls_from_file(args.file)
        print(f"\n[RESULT] {saved} new jobs imported from file")
    
    elif args.command == "add":
        success = add_manual_url(args.url, args.title, args.company)
        print(f"\n[RESULT] {'Added' if success else 'Failed to add'} URL")
    
    elif args.command == "list":
        jobs = get_pending_jobs(50)
        if jobs:
            print(f"\n{'='*70}")
            print(f"PENDING JOBS: {len(jobs)}")
            print(f"{'='*70}")
            for j in jobs:
                print(f"  [{j['platform']}] {j['title'] or 'N/A'} | {j['company']}")
                print(f"    URL: {j['url']}")
        else:
            print("[INFO] No pending jobs in database")
    
    elif args.command == "stats":
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE applied = 1")
        applied = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs WHERE applied = 0")
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT platform, COUNT(*) FROM jobs GROUP BY platform")
        platforms = cursor.fetchall()
        
        conn.close()
        
        print(f"\n{'='*50}")
        print(f"SCRAPER STATISTICS")
        print(f"{'='*50}")
        print(f"  Total jobs: {total}")
        print(f"  Applied: {applied}")
        print(f"  Pending: {pending}")
        print(f"\n  By Platform:")
        for p, c in platforms:
            print(f"    {p}: {c}")


if __name__ == "__main__":
    main()
