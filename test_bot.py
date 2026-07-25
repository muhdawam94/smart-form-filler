"""
TEST BOT - Verifikasi semua komponen berfungsi
Jalankan: python test_bot.py
"""
import os
import sys
import asyncio
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


def test_imports():
    """Test semua import"""
    print("="*50)
    print("TEST 1: Import Libraries")
    print("="*50)
    
    try:
        from playwright.async_api import async_playwright
        print("  [OK] Playwright")
    except ImportError:
        print("  [FAIL] Playwright - run: pip install playwright")
        return False
    
    try:
        from groq import Groq
        print("  [OK] Groq")
    except ImportError:
        print("  [FAIL] Groq - run: pip install groq")
        return False
    
    try:
        from dotenv import load_dotenv
        print("  [OK] python-dotenv")
    except ImportError:
        print("  [FAIL] python-dotenv - run: pip install python-dotenv")
        return False
    
    from config import get_config
    from core import SmartFormFiller, PlatformDetector, AIFieldAnalyzer
    print("  [OK] Project modules")
    
    return True


def test_config():
    """Test configuration"""
    print("\n" + "="*50)
    print("TEST 2: Configuration")
    print("="*50)
    
    from config import get_config
    config = get_config()
    
    checks = [
        ("GROQ API Key", bool(config.ai.groq_api_key)),
        ("Full Name", bool(config.personal.full_name)),
        ("Email", bool(config.personal.email)),
        ("Phone", bool(config.personal.phone)),
        ("Skills loaded", len(config.personal.skills) > 0),
    ]
    
    all_ok = True
    for name, ok in checks:
        print(f"  {'[OK]' if ok else '[WARN]'} {name}")
        if not ok:
            all_ok = False
    
    return all_ok


def test_database():
    """Test database"""
    print("\n" + "="*50)
    print("TEST 3: Database")
    print("="*50)
    
    db_path = os.path.join(os.path.dirname(__file__), "data", "jobs.db")
    
    if not os.path.exists(db_path):
        print("  [WARN] Database not found, initializing...")
        from data.init_db import init_database
        init_database()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"  [OK] Tables: {', '.join(tables)}")
    
    # Count jobs
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]
    print(f"  [OK] Jobs in database: {total}")
    
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE applied = 0")
    pending = cursor.fetchone()[0]
    print(f"  [OK] Pending jobs: {pending}")
    
    conn.close()
    return True


def test_platform_detector():
    """Test platform detection"""
    print("\n" + "="*50)
    print("TEST 4: Platform Detection")
    print("="*50)
    
    from core import PlatformDetector
    detector = PlatformDetector()
    
    test_urls = [
        ("https://boards.greenhouse.io/company/jobs/123", "greenhouse"),
        ("https://jobs.lever.co/company", "lever"),
        ("https://jobs.ashbyhq.com/company", "ashby"),
        ("https://company.wd5.myworkdayjobs.com/en-US", "workday"),
        ("https://example.com/apply", "unknown"),
    ]
    
    all_ok = True
    for url, expected in test_urls:
        result = detector.detect(url=url)
        ok = result == expected
        print(f"  {'[OK]' if ok else '[FAIL]'} {url[:40]}... -> {result}")
        if not ok:
            all_ok = False
    
    return all_ok


async def test_browser():
    """Test browser"""
    print("\n" + "="*50)
    print("TEST 5: Browser")
    print("="*50)
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto('https://example.com', timeout=10000)
            title = await page.title()
            
            print(f"  [OK] Browser launches successfully")
            print(f"  [OK] Can navigate to pages (title: {title})")
            
            await browser.close()
            print(f"  [OK] Browser closes cleanly")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Browser error: {e}")
        return False


async def test_ai():
    """Test AI connection"""
    print("\n" + "="*50)
    print("TEST 6: AI Connection (Groq)")
    print("="*50)
    
    try:
        from groq import Groq
        from config import get_config
        
        config = get_config()
        client = Groq(api_key=config.ai.groq_api_key)
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Say 'AI is working' in one sentence."}],
            temperature=0.7,
            max_tokens=50,
        )
        
        result = response.choices[0].message.content.strip()
        print(f"  [OK] AI Response: {result[:50]}")
        return True
    except Exception as e:
        print(f"  [FAIL] AI Error: {e}")
        return False


def test_telegram():
    """Test Telegram notification"""
    print("\n" + "="*50)
    print("TEST 7: Telegram")
    print("="*50)
    
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        # Try loading from .env
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if token and chat_id:
        print(f"  [OK] Token configured: {token[:10]}...")
        print(f"  [OK] Chat ID configured: {chat_id}")
        
        # Send test message
        import requests
        try:
            msg = "Bot test message - Smart Form Filler is ready!"
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg},
                timeout=10,
            )
            if resp.status_code == 200:
                print(f"  [OK] Test message sent successfully")
            else:
                print(f"  [WARN] Message send failed: {resp.status_code}")
        except Exception as e:
            print(f"  [WARN] Could not send test message: {e}")
        
        return True
    else:
        print("  [WARN] Telegram not configured")
        print("  [INFO] Set TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False


async def main():
    """Run all tests"""
    print("\n" + "#"*50)
    print("# SMART FORM FILLER - System Test")
    print("#"*50)
    
    results = {}
    
    results["imports"] = test_imports()
    results["config"] = test_config()
    results["database"] = test_database()
    results["detector"] = test_platform_detector()
    results["browser"] = await test_browser()
    results["ai"] = await test_ai()
    results["telegram"] = test_telegram()
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, ok in results.items():
        print(f"  {'[PASS]' if ok else '[FAIL]'} {name}")
    
    print(f"\n  Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  ALL TESTS PASSED! Bot is ready to use.")
        print("\n  Next steps:")
        print("  1. Add jobs: python job_scraper.py greenhouse <company>")
        print("  2. Test fill: python main.py fill <URL> --dry-run")
        print("  3. Run bot: python scheduler_runner.py")
    else:
        print("\n  Some tests failed. Please fix the issues above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
