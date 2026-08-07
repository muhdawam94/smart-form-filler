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
# WEB3 JOBS RADAR SCRAPER (gratis, tanpa API key)
# =============================================
async def scrape_web3jobsradar(query: str = "", remote: bool = True, limit: int = 50) -> list:
    """Scrape jobs dari web3jobsradar.com - GRATIS, no auth needed.
    API lambat, pakai retry + timeout besar."""
    import requests
    
    params = {"limit": min(limit, 50)}
    if query:
        params["q"] = query
    
    url = "https://web3jobsradar.com/api/jobs"
    print(f"[SCRAPE] Web3JobsRadar: query={query or 'all'}, remote={remote}")
    
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            jobs = []
            for job in data.get("jobs", []):
                if remote:
                    remote_val = str(job.get("remote", "")).lower().strip()
                    if remote_val and remote_val not in ("remote", "true", "yes", "1", "fully remote", "fully-remote"):
                        continue
                
                apply_url = job.get("applyUrl") or job.get("url") or ""
                if not apply_url:
                    continue
                jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "url": apply_url,
                    "platform": detect_platform_from_url(apply_url),
                    "location": job.get("location", "Remote"),
                    "description": ", ".join(job.get("tags", [])) if isinstance(job.get("tags"), list) else str(job.get("tags", "")),
                })
            
            print(f"  [OK] Found {len(jobs)} jobs")
            return jobs
        except requests.exceptions.Timeout:
            wait = (attempt + 1) * 10
            print(f"  [TIMEOUT] Attempt {attempt+1}/3, retrying in {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"  [ERROR] {e}")
            return []
    
    print(f"  [FAILED] All 3 attempts timed out")
    return []


# =============================================
# WEB3.CAREER SCRAPER (gratis dengan token)
# =============================================
async def scrape_web3career(token: str = "", tag: str = "", remote: bool = True, limit: int = 50) -> list:
    """Scrape jobs dari web3.career - GRATIS dengan API token"""
    import requests
    
    api_token = token or os.getenv("WEB3_CAREER_TOKEN", "")
    if not api_token:
        print("[SCRAPE] Web3.career: No token provided, skipping")
        return []
    
    params = {"token": api_token, "limit": min(limit, 100)}
    if tag:
        params["tag"] = tag
    if remote:
        params["remote"] = "true"
    
    url = "https://web3.career/api/v1"
    print(f"[SCRAPE] Web3.career: tag={tag or 'all'}, remote={remote}")
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # API returns [docs_string, params_string, jobs_array] or {jobs: [...]}
        jobs_list = []
        if isinstance(data, list) and len(data) >= 3:
            jobs_list = data[2] if isinstance(data[2], list) else []
        elif isinstance(data, list) and len(data) >= 2:
            jobs_list = data[1] if isinstance(data[1], list) else []
        elif isinstance(data, dict):
            jobs_list = data.get("jobs", [])
        
        jobs = []
        for job in jobs_list:
            if not isinstance(job, dict):
                continue
            apply_url = job.get("apply_url") or job.get("url") or ""
            if not apply_url:
                continue
            jobs.append({
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "url": apply_url,
                "platform": detect_platform_from_url(apply_url),
                "location": job.get("location", "Remote"),
                "description": job.get("description", "")[:500] if job.get("description") else "",
            })
        
        print(f"  [OK] Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


# =============================================
# CRYPTOJOBSLIST.COM SCRAPER (HTML parsing, no auth)
# =============================================
async def scrape_cryptojobslist(tag: str = "", remote: bool = True, limit: int = 50) -> list:
    """CryptoJobsList blocks scrapers (403). Kept as stub for future use."""
    print("[SCRAPE] CryptoJobsList: site blocks automated access (403)")
    return []


# =============================================
# WEB3.CAREER HTML SCRAPER (no token needed)
# =============================================
async def scrape_web3career_html(tag: str = "", remote: bool = True, limit: int = 50) -> list:
    """Scrape jobs dari web3.career tanpa API token - pakai HTML parsing"""
    import requests
    import re
    
    if tag:
        page_url = f"https://web3.career/{tag.replace(' ', '+')}-jobs"
    elif remote:
        page_url = "https://web3.career/remote-jobs"
    else:
        page_url = "https://web3.career/"
    
    print(f"[SCRAPE] Web3.career HTML: tag={tag or 'all'}, remote={remote}")
    
    try:
        resp = requests.get(page_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        html = resp.text
        
        jobs = []
        # web3.career uses table rows with onclick="tableTurboRowClick(event, '/slug/id')"
        row_pattern = re.compile(
            r'onclick="tableTurboRowClick\(event,\s*\'(/[^\']+/(\d+))\'\)"',
            re.IGNORECASE
        )
        
        # Also find h2 (company) and h3 (title) tags within the table
        # Structure: <tr> ... <h2>Company</h2> ... <h3>Job Title</h3> ... </tr>
        # Split HTML by table rows to match company+title to each link
        row_blocks = re.split(r'<tr\b', html)
        
        seen_urls = set()
        for block in row_blocks:
            link_match = row_pattern.search(block)
            if not link_match:
                continue
            
            path = link_match.group(1)
            job_url = f"https://web3.career{path}"
            
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)
            
            if len(jobs) >= limit:
                break
            
            # Extract company from h2 tag
            company_match = re.search(r'<h2[^>]*>(.*?)</h2>', block, re.DOTALL)
            company = ""
            if company_match:
                company = re.sub(r'<[^>]+>', '', company_match.group(1)).strip()
            
            # Extract title from h3 tag
            title_match = re.search(r'<h3[^>]*>(.*?)</h3>', block, re.DOTALL)
            title = ""
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            
            # If no h3 title, try <a> tag text
            if not title:
                a_match = re.search(r'<a[^>]*>([^<]+)</a>', block)
                if a_match:
                    title = a_match.group(1).strip()
            
            platform = detect_platform_from_url(job_url)
            jobs.append({
                "title": title,
                "company": company,
                "url": job_url,
                "platform": platform,
                "location": "Remote" if remote else "",
                "description": tag,
            })
        
        print(f"  [OK] Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


# =============================================
# GREENHOUSE BULK SCRAPER (banyak Web3 companies)
# =============================================
# Web3/crypto companies yang pakai Greenhouse (verified: return 200 + jobs)
WEB3_GREENHOUSE_COMPANIES = [
    "coinbase", "robinhood", "discord", "figma", "gitlab",
    "vercel", "stripe", "airtable", "cloudflare", "databricks",
    "twitch", "reddit", "flowtraders", "blockchain", "okx",
]

async def scrape_greenhouse_bulk(companies: list = None, limit_per_company: int = 30) -> list:
    """Scrape banyak Greenhouse companies sekaligus"""
    if companies is None:
        companies = WEB3_GREENHOUSE_COMPANIES
    
    all_jobs = []
    for company in companies:
        jobs = await scrape_greenhouse_board(company)
        # Batasi per company
        all_jobs.extend(jobs[:limit_per_company])
    
    print(f"[SCRAPE] Greenhouse bulk: {len(all_jobs)} total jobs from {len(companies)} companies")
    return all_jobs


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


def get_pending_jobs(limit: int = 10, include_failed: bool = True, max_retries: int = 2) -> list:
    """Ambil jobs yang belum di-apply atau perlu di-retry, dengan prioritas seimbang.
    Hanya job yang relevan dengan profil developer yang dikembalikan."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Score lebih seimbang - semua platform punya kesempatan yang sama
    cursor.execute("""
        UPDATE jobs SET score = CASE
            WHEN platform = 'greenhouse' THEN 8
            WHEN platform = 'ashby' THEN 7
            WHEN platform = 'lever' THEN 7
            WHEN platform = 'smartrecruiters' THEN 6
            ELSE 5
        END
        WHERE status = 'pending'
    """)
    conn.commit()
    
    # Ambil lebih banyak kandidat karena akan difilter relevansi
    fetch_limit = limit * 4
    
    # Ambil pending jobs, atau failed jobs yang masih bisa di-retry
    if include_failed:
        cursor.execute("""
            SELECT id, title, company, url, platform, location
            FROM jobs
            WHERE (applied = 0 AND status = 'pending')
               OR (status = 'failed' AND retry_count < ?)
            ORDER BY score DESC, created_at DESC
            LIMIT ?
        """, (max_retries, fetch_limit))
    else:
        cursor.execute("""
            SELECT id, title, company, url, platform, location
            FROM jobs
            WHERE applied = 0 AND status = 'pending'
            ORDER BY score DESC, created_at DESC
            LIMIT ?
        """, (fetch_limit,))
    
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
    
    # Filter hanya job yang relevan dengan profil developer
    filtered = [j for j in jobs if is_relevant_job_title(j.get("title", ""))]
    return filtered[:limit]


TECH_TITLE_PATTERNS = re.compile(
    r"\b(engineer|engineering|developer|development|dev\b|software|backend|frontend|"
    r"full[- ]stack|solidity|smart[- ]?contract|blockchain|web3|rust|python|javascript|"
    r"typescript|react|node|defi|crypto|sre|devops|platform|infrastructure|"
    r"security engineer|data engineer|ml engineer|ai engineer|qa engineer|"
    r"front[- ]end|back[- ]end|contract engineer|protocol)\b",
    re.IGNORECASE,
)

NON_TECH_TITLE_PATTERNS = re.compile(
    r"\b(sales|marketing|legal|counsel|human resources|\bhr\b|recruiting|recruiter|"
    r"talent|accounting|finance|financial|cashier|customer support|support specialist|"
    r"support|business development|community manager|customer success|operations manager|"
    r"compliance|policy|people\b|office|admin|account manager|account executive|"
    r"writer|content|designer|design lead|brand)\b",
    re.IGNORECASE,
)


def is_relevant_job_title(title: str) -> bool:
    """Apakah judul job relevan dengan profil developer/engineer."""
    if not title:
        return False
    t = title.lower()
    # Job teknis -> relevan
    if TECH_TITLE_PATTERNS.search(t):
        return True
    # Job non-teknis yang jelas -> skip
    if NON_TECH_TITLE_PATTERNS.search(t):
        return False
    # Tidak jelas -> biarkan masuk (filter tidak agresif)
    return True


def mark_job_applied(job_id: int, success: bool, max_retries: int = 2):
    """Tandai job sudah di-apply. Jika gagal, masih bisa di-retry sampai max_retries."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if success:
        status = "applied"
        cursor.execute("""
            UPDATE jobs
            SET applied = 1, applied_at = ?, status = ?, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), status, datetime.now().isoformat(), job_id))
    else:
        # Cek berapa kali sudah di-retry
        cursor.execute("SELECT retry_count FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        current_retries = row[0] if row else 0
        
        if current_retries + 1 >= max_retries:
            # Sudah max retries, mark sebagai permanently failed
            cursor.execute("""
                UPDATE jobs
                SET applied = 1, status = 'failed', retry_count = retry_count + 1, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), job_id))
        else:
            # Belum max retries, mark gagal tapi masih bisa di-retry
            cursor.execute("""
                UPDATE jobs
                SET status = 'failed', retry_count = retry_count + 1, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), job_id))
    
    conn.commit()
    conn.close()


def reset_failed_jobs():
    """Reset semua failed jobs agar bisa di-retry"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs SET status = 'pending', applied = 0, retry_count = 0, updated_at = ?
        WHERE status = 'failed'
    """, (datetime.now().isoformat(),))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


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
    
    # Scrape Web3JobsRadar (gratis, no auth)
    w3r_parser = subparsers.add_parser("web3jobsradar", help="Scrape Web3JobsRadar (free)")
    w3r_parser.add_argument("--query", default="", help="Search query (e.g., 'marketing')")
    w3r_parser.add_argument("--no-remote", action="store_true", help="Include on-site jobs")
    w3r_parser.add_argument("--limit", type=int, default=50, help="Max jobs to scrape")
    
    # Scrape Web3.career (needs token)
    w3c_parser = subparsers.add_parser("web3career", help="Scrape Web3.career (needs token)")
    w3c_parser.add_argument("--token", default="", help="API token")
    w3c_parser.add_argument("--tag", default="", help="Filter by tag (e.g., 'marketing')")
    w3c_parser.add_argument("--no-remote", action="store_true", help="Include on-site jobs")
    w3c_parser.add_argument("--limit", type=int, default=50, help="Max jobs to scrape")
    
    # Scrape Web3 Greenhouse bulk
    w3gh_parser = subparsers.add_parser("web3-greenhouse", help="Scrape Web3 companies on Greenhouse")
    w3gh_parser.add_argument("--limit", type=int, default=20, help="Max jobs per company")
    
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
    
    # Scrape all Web3 sources
    subparsers.add_parser("scrape-all", help="Scrape all Web3 job sources")
    
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
    
    elif args.command == "web3jobsradar":
        jobs = asyncio.run(scrape_web3jobsradar(
            query=args.query, remote=not args.no_remote, limit=args.limit
        ))
        saved = save_jobs_to_db(jobs, source="web3jobsradar")
        print(f"\n[RESULT] {saved} new jobs saved to database")
    
    elif args.command == "web3career":
        jobs = asyncio.run(scrape_web3career(
            token=args.token, tag=args.tag, remote=not args.no_remote, limit=args.limit
        ))
        saved = save_jobs_to_db(jobs, source="web3career")
        print(f"\n[RESULT] {saved} new jobs saved to database")
    
    elif args.command == "web3-greenhouse":
        jobs = asyncio.run(scrape_greenhouse_bulk(limit_per_company=args.limit))
        saved = save_jobs_to_db(jobs, source="web3_greenhouse")
        print(f"\n[RESULT] {saved} new jobs saved to database")
    
    elif args.command == "scrape-all":
        print("[SCRAPE-ALL] Scraping all Web3 job sources...")
        all_saved = 0
        
        # 1. Web3JobsRadar - multiple queries (gratis, fokus developer/engineer)
        for q in ["", "developer", "engineer", "backend", "frontend", "blockchain",
                  "solidity", "smart contract", "full stack", "python", "react", "web3"]:
            jobs = asyncio.run(scrape_web3jobsradar(query=q, remote=True, limit=50))
            all_saved += save_jobs_to_db(jobs, source="web3jobsradar")
        
        # 2. Greenhouse Web3 companies
        jobs = asyncio.run(scrape_greenhouse_bulk(limit_per_company=15))
        all_saved += save_jobs_to_db(jobs, source="web3_greenhouse")
        
        # 3. Web3.career HTML (no token)
        jobs = asyncio.run(scrape_web3career_html(remote=True, limit=50))
        all_saved += save_jobs_to_db(jobs, source="web3career_html")
        
        # 4. Web3.career API (jika ada token)
        if os.getenv("WEB3_CAREER_TOKEN"):
            for tag in ["", "marketing", "engineering", "community"]:
                jobs = asyncio.run(scrape_web3career(tag=tag, remote=True, limit=50))
                all_saved += save_jobs_to_db(jobs, source="web3career")
        
        # 5. CryptoJobsList
        jobs = asyncio.run(scrape_cryptojobslist(remote=True, limit=50))
        all_saved += save_jobs_to_db(jobs, source="cryptojobslist")
        
        print(f"\n[RESULT] Total: {all_saved} new jobs saved to database")
    
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
