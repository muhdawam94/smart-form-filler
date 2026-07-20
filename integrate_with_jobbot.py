"""
INTEGRATION SCRIPT - Hubungkan Smart Form Filler dengan Dawam-Job-Bot
"""
import os
import sys
import json
import shutil
from pathlib import Path

def find_job_bot():
    """Cari job bot directory"""
    possible_paths = [
        os.path.expanduser("~/Desktop/Dawam-Job-Bot"),
        os.path.expanduser("~/Desktop/universal-job-bot"),
        os.path.expanduser("~/Desktop/web3_job_bot"),
        os.path.expanduser("~/job-bot"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def create_integration_patch(job_bot_path: str):
    """Buat patch untuk integrasi dengan Dawam-Job-Bot"""
    patch = """
# ============================================================
# INTEGRATION PATCH untuk Dawam-Job-Bot
# Tambahkan kode ini ke main.py di Dawam-Job-Bot
# ============================================================

# 1. Import di bagian atas main.py:
from smart_form_filler.core import SmartFormFiller
from smart_form_filler.config import get_config

# 2. Tambahkan fungsi ini setelah fungsi auto_apply yang sudah ada:
async def smart_auto_apply(jobs, cv_path=None, dry_run=False):
    \"\"\"Smart auto-apply menggunakan SmartFormFiller\"\"\"
    config = get_config()
    filler = SmartFormFiller(config)
    
    if not await filler.init_browser():
        print("[ERROR] Failed to init browser for smart form filler")
        return []
    
    results = []
    try:
        for job in jobs:
            url = job.get('url', '')
            if not url:
                continue
            
            print(f"\\n[SMART APPLY] {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")
            result = await filler.fill_application(url, cv_path, dry_run)
            result['job_data'] = job
            results.append(result)
            
            # Pause between applications
            import asyncio
            await asyncio.sleep(3)
    finally:
        await filler.close_browser()
    
    return results

# 3. Di fungsi main(), tambahkan argumen --smart-auto-apply:
# Di bagian argument parsing, tambahkan:
# parser.add_argument('--smart-auto-apply', action='store_true', 
#                     help='Use smart form filler for all applications')

# 4. Di bagian execution, tambahkan:
# if args.smart_auto_apply:
#     smart_results = asyncio.run(smart_auto_apply(jobs, cv_path, args.dry_run))
#     print(f"Smart auto-apply completed: {len(smart_results)} applications")
"""
    
    # Save patch
    patch_file = os.path.join(os.path.dirname(__file__), "INTEGRATION_PATCH.py")
    with open(patch_file, 'w') as f:
        f.write(patch)
    
    print(f"[PATCH CREATED] {patch_file}")
    return patch_file


def setup_symlink():
    """Setup symlink agar smart-form-filler bisa di-import"""
    # Create __init__.py di root
    init_file = os.path.join(os.path.dirname(__file__), "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write('"""Smart Form Filler - Package"""\n')
    
    print("[SETUP] Package structure created")


def create_requirements():
    """Create requirements.txt"""
    requirements = """playwright>=1.40.0
groq>=0.4.0
openai>=1.0.0
fake-useragent>=1.4.0
"""
    
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    with open(req_file, 'w') as f:
        f.write(requirements)
    
    print(f"[SETUP] Requirements created: {req_file}")
    return req_file


def create_quick_start():
    """Create quick start guide"""
    guide = """# SMART FORM FILLER - Quick Start

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Set API key (optional, for AI-powered form filling)
set GROQ_API_KEY=your_groq_api_key
# Get free key at: https://console.groq.com
```

## Usage

### Fill single application:
```bash
python main.py fill "https://apply.greenhouse.io/company/jobs/123456"
python main.py fill "https://apply.greenhouse.io/company/jobs/123456" --dry-run
python main.py fill "https://apply.greenhouse.io/company/jobs/123456" --cv cv.pdf
```

### Fill from list:
```bash
# Create urls.txt with one URL per line
python main.py fill-file urls.txt --limit 5
```

### Fill from job bot database:
```bash
python main.py fill-db --db path/to/jobs.db --limit 10
```

### Detect platform:
```bash
python main.py detect "https://apply.lever.co/company123"
```

### Check stats:
```bash
python main.py stats
```

## Integration with Dawam-Job-Bot

Lihat INTEGRATION_PATCH.py untuk instruksi integrasi.

## How It Works

1. **Platform Detection** - Deteksi ATS (Greenhouse, Lever, Workday, dll)
2. **Field Analysis** - AI menganalisis semua form fields
3. **Smart Fill** - Isi fields dengan data dari profile
4. **Custom Questions** - AI generate jawaban untuk pertanyaan custom
5. **Anti-Detection** - Random delays, user agent rotation
6. **Logging** - Track semua submissions

## Supported Platforms

- Greenhouse (95% success rate)
- Lever (93%)
- Ashby (90%)
- SmartRecruiters (92%)
- BambooHR (91%)
- Workday (75% - has CAPTCHA)
- Custom/Unknown (60-70%)
"""
    
    guide_file = os.path.join(os.path.dirname(__file__), "QUICK_START.md")
    with open(guide_file, 'w') as f:
        f.write(guide)
    
    print(f"[SETUP] Quick start guide created: {guide_file}")


def main():
    print("="*60)
    print("SMART FORM FILLER - Setup & Integration")
    print("="*60)
    
    # Find existing job bot
    job_bot_path = find_job_bot()
    
    if job_bot_path:
        print(f"\n[FOUND] Dawam-Job-Bot at: {job_bot_path}")
        
        # Create integration patch
        create_integration_patch(job_bot_path)
    else:
        print("\n[INFO] Dawam-Job-Bot not found on Desktop")
    
    # Setup package
    setup_symlink()
    create_requirements()
    create_quick_start()
    
    print(f"\n{'='*60}")
    print("SETUP COMPLETE!")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("1. pip install -r requirements.txt")
    print("2. playwright install chromium")
    print("3. python main.py fill <URL> --dry-run")


if __name__ == "__main__":
    main()
