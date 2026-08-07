"""Demo: Apply2 jobs in visible browser"""
import asyncio
import sys
sys.path.insert(0, '.')

from config import get_config
from core.form_filler import SmartFormFiller

JOBS = [
    ("Senior APAC Growth Marketing Manager", "QuickNode", "https://jobs.ashbyhq.com/quicknode/6294e254-3872-4eb3-b2df-8aa876ad0b42"),
    ("Campaigns & Memberships Marketing Manager", "Elliptic", "https://jobs.ashbyhq.com/elliptic/6562f4e6-c78d-49f2-ad82-68a00b1ab458"),
]

async def main():
    config = get_config()
    config.headless = False  # Show browser
    filler = SmartFormFiller(config)
    
    await filler.init_browser()
    
    for title, company, url in JOBS:
        print(f"\n{'='*60}")
        print(f"Applying: {title} @ {company}")
        print(f"URL: {url}")
        print(f"{'='*60}")
    
        try:
            result = await filler.fill_application(url, dry_run=False)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")
    
    await filler.close_browser()
    input("\nDone! Press Enter to exit...")

if __name__ == "__main__":
    asyncio.run(main())
