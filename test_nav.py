import asyncio
from playwright.async_api import async_playwright

async def test():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
    page = await browser.new_page()
    
    print("Navigating...")
    try:
        await page.goto("https://boards.greenhouse.io/robinhood/jobs/8060605", 
                        wait_until="domcontentloaded", timeout=30000)
        print("Page loaded")
        await page.wait_for_timeout(3000)
        
        # Click apply
        btn = await page.query_selector("a:has-text('Apply')")
        if btn:
            await btn.click()
            print("Clicked apply")
            await page.wait_for_timeout(3000)
        
        # Check fields
        inputs = await page.query_selector_all("input, textarea, select")
        print(f"Found {len(inputs)} fields")
        
        for inp in inputs[:10]:
            name = await inp.get_attribute("name") or ""
            ftype = await inp.get_attribute("type") or "text"
            print(f"  {ftype}: {name}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    await browser.close()
    await pw.stop()

asyncio.run(test())
