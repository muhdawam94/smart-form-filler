import asyncio
import time
import sys
from core import SmartFormFiller
from config import get_config

def p(msg):
    print(msg, flush=True)

async def test():
    config = get_config()
    filler = SmartFormFiller(config)
    ok = await filler.init_browser()
    if not ok:
        p("Browser failed")
        return
    
    try:
        url = "https://boards.greenhouse.io/robinhood/jobs/8060605"
        
        t0 = time.time()
        await filler.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        p(f"1. Navigate: {time.time()-t0:.1f}s")
        
        await filler.page.wait_for_timeout(2000)
        
        t0 = time.time()
        await filler._click_apply_button()
        p(f"2. Apply button: {time.time()-t0:.1f}s")
        
        t0 = time.time()
        await filler._handle_iframes()
        p(f"3. Iframes: {time.time()-t0:.1f}s")
        
        t0 = time.time()
        page_source = await filler.page.content()
        p(f"4. Page source: {time.time()-t0:.1f}s")
        
        from core.platform_detector import PlatformDetector
        from core.ai_field_analyzer import AIFieldAnalyzer
        detector = PlatformDetector()
        analyzer = AIFieldAnalyzer(config)
        
        t0 = time.time()
        platform = detector.detect(url=url, page_source=page_source)
        strategy = detector.get_form_strategy(platform)
        p(f"5. Detect: {platform} in {time.time()-t0:.1f}s")
        
        t0 = time.time()
        captcha_info = analyzer.detect_captcha(page_source)
        p(f"6. Captcha detect: {time.time()-t0:.1f}s")
        
        t0 = time.time()
        job_context = analyzer.extract_job_context(page_source, url)
        p(f"7. Job context: {time.time()-t0:.1f}s")
        
        filler._last_job_context = job_context
        
        t0 = time.time()
        fields = await filler._detect_fields_by_selector()
        p(f"8. Fields: {len(fields)} in {time.time()-t0:.1f}s")
        
        filled_count = 0
        skipped_count = 0
        
        for i, field in enumerate(fields):
            t1 = time.time()
            try:
                filled = await filler._fill_field(field, None)
                elapsed = time.time() - t1
                name = field.get("field_name", "?")
                if filled:
                    filled_count += 1
                    p(f"  [{i}] FILLED {name} ({elapsed:.1f}s)")
                else:
                    skipped_count += 1
                    p(f"  [{i}] SKIP {name} ({elapsed:.1f}s)")
            except Exception as e:
                skipped_count += 1
                p(f"  [{i}] ERROR {name}: {e} ({time.time()-t1:.1f}s)")
        
        p(f"\nTotal: filled={filled_count}, skipped={skipped_count}")
        
    except Exception as e:
        p(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await filler.close_browser()
        p("Browser closed")

asyncio.run(test())
