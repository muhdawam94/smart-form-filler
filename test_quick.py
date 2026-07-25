import asyncio
from core import SmartFormFiller
from config import get_config

async def test():
    config = get_config()
    filler = SmartFormFiller(config)
    ok = await filler.init_browser()
    if not ok:
        print("Browser failed")
        return
    
    try:
        result = await filler.fill_application(
            "https://boards.greenhouse.io/robinhood/jobs/8060605",
            dry_run=True
        )
        status = result["status"]
        filled = result["fields_filled"]
        skipped = result["fields_skipped"]
        print(f"Status: {status}")
        print(f"Filled: {filled}")
        print(f"Skipped: {skipped}")
    finally:
        await filler.close_browser()

asyncio.run(test())
