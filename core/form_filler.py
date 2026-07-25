"""
FORM FILLER - Isi form secara otomatis menggunakan Playwright
Handles semua jenis form: text, dropdown, checkbox, file upload, dll
"""
import asyncio
import json
import os
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .platform_detector import PlatformDetector
from .ai_field_analyzer import AIFieldAnalyzer


class SmartFormFiller:
    """Smart form filler yang bisa handle semua jenis application forms"""
    
    def __init__(self, config):
        self.config = config
        self.detector = PlatformDetector()
        self.ai_analyzer = AIFieldAnalyzer(config)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.submissions = []
        
        # Load submission history
        if os.path.exists(config.submissions_log):
            with open(config.submissions_log, 'r') as f:
                self.submissions = json.load(f)
    
    async def init_browser(self):
        """Initialize Playwright browser"""
        if not PLAYWRIGHT_AVAILABLE:
            print("[ERROR] Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=self._get_random_user_agent(),
            locale="en-US",
            timezone_id="Asia/Jakarta",
        )
        
        self.page = await self.context.new_page()
        
        # Anti-detection scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        return True
    
    async def close_browser(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def fill_application(self, url: str, cv_path: str = None, 
                                dry_run: bool = False) -> Dict:
        """Main method: Isi application form di URL"""
        print(f"\n{'='*60}")
        print(f"FILLING APPLICATION: {url}")
        print(f"{'='*60}")
        
        result = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "platform": "unknown",
            "status": "pending",
            "fields_filled": 0,
            "fields_skipped": 0,
            "errors": [],
            "captcha_detected": False,
            "custom_questions": 0,
            "dry_run": dry_run,
        }
        
        try:
            # Navigate to page
            await self.page.goto(url, wait_until="domcontentloaded", 
                               timeout=self.config.timeout)
            await self._random_delay()
            
            # Wait for page to be ready
            await self.page.wait_for_timeout(2000)
            
            # Try to find and click Apply button to load the form
            await self._click_apply_button()
            
            # Check for iframes (many career pages embed forms in iframes)
            await self._handle_iframes()
            
            # Detect platform
            page_source = await self.page.content()
            platform = self.detector.detect(url=url, page_source=page_source)
            result["platform"] = platform
            strategy = self.detector.get_form_strategy(platform)
            
            print(f"[DETECTED] Platform: {platform}")
            print(f"[STRATEGY] Method: {strategy['method']}")
            print(f"[ESTIMATED] Time: {strategy['estimated_time']}")
            
            # Check for CAPTCHA
            captcha_info = self.ai_analyzer.detect_captcha(page_source)
            result["captcha_detected"] = captcha_info["has_captcha"]
            
            if captcha_info["has_captcha"]:
                print(f"[WARNING] CAPTCHA detected: {captcha_info['captcha_types']}")
                # If it's hCaptcha or reCAPTCHA, these are nearly impossible to bypass
                hard_captcha = [c for c in captcha_info["captcha_types"] if c in ("hcaptcha", "recaptcha")]
                if hard_captcha:
                    print(f"[SKIP] Hard CAPTCHA ({hard_captcha}) - cannot auto-fill")
                    result["status"] = "captcha_blocked"
                    self._log_submission(result)
                    return result
            
            # Extract job context for better answers
            job_context = self.ai_analyzer.extract_job_context(page_source, url)
            print(f"[CONTEXT] Job context extracted")
            
            # Analyze form fields
            fields = await self._analyze_fields(page_source, url)
            print(f"[FIELDS] Found {len(fields)} form fields")
            
            # Fill each field
            for field in fields:
                try:
                    filled = await self._fill_field(field, cv_path)
                    if filled:
                        result["fields_filled"] += 1
                        if field.get("field_type") == "textarea" and "?" in str(field.get("field_name", "")):
                            result["custom_questions"] += 1
                    else:
                        result["fields_skipped"] += 1
                except Exception as e:
                    result["errors"].append(f"Error filling {field.get('field_name', 'unknown')}: {str(e)}")
                    result["fields_skipped"] += 1
                
                await self._random_delay()
            
            # Submit if not dry run
            if not dry_run and result["fields_filled"] > 0:
                submitted = await self._submit_form(strategy)
                result["status"] = "submitted" if submitted else "submit_failed"
            else:
                result["status"] = "dry_run" if dry_run else "filled_not_submitted"
            
            print(f"\n[RESULT] Status: {result['status']}")
            print(f"[RESULT] Fields filled: {result['fields_filled']}")
            print(f"[RESULT] Fields skipped: {result['fields_skipped']}")
            print(f"[RESULT] Custom questions: {result['custom_questions']}")
            
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            print(f"[ERROR] {e}")
        
        self._log_submission(result)
        return result
    
    async def _click_apply_button(self):
        """Click Apply button jika ada untuk membuka form"""
        try:
            apply_selectors = [
                "a:has-text('Apply')",
                "button:has-text('Apply')",
                "[data-testid='apply']",
                ".apply-btn",
                "#apply-btn",
                "a[href*='apply']",
            ]
            
            for selector in apply_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn:
                        is_visible = await btn.is_visible()
                        if is_visible:
                            print(f"[APPLY] Found apply button, clicking...")
                            await btn.click()
                            await self.page.wait_for_timeout(3000)
                            return
                except:
                    continue
        except Exception as e:
            print(f"[APPLY] Error clicking apply: {e}")
    
    async def _handle_iframes(self):
        """Check dan handle jika form ada di dalam iframe"""
        try:
            iframes = await self.page.query_selector_all("iframe")
            
            # Iframe indicators that are CAPTCHA-related - SKIP these
            captcha_indicators = ["hcaptcha", "recaptcha", "captcha", "turnstile", "challenge"]
            
            for iframe in iframes:
                src = (await iframe.get_attribute("src") or "").lower()
                name = (await iframe.get_attribute("name") or "").lower()
                
                # Skip CAPTCHA iframes entirely
                if any(ind in src or ind in name for ind in captcha_indicators):
                    print(f"[IFRAME] Skipping CAPTCHA iframe: {src or name}")
                    continue
                
                # Check if it's a form-related iframe
                form_indicators = ["apply", "form", "application", "greenhouse", "lever", "ashby"]
                if any(ind in src or ind in name for ind in form_indicators):
                    print(f"[IFRAME] Found form iframe: {src or name}")
                    
                    # Try to switch to iframe
                    frame = await iframe.content_frame()
                    if frame:
                        # Check for form fields in iframe
                        inputs = await frame.query_selector_all("input, textarea, select")
                        if inputs:
                            # Verify it's not just a CAPTCHA widget inside
                            field_names = []
                            for inp in inputs[:10]:
                                ftype = await inp.get_attribute("type") or "text"
                                fname = await inp.get_attribute("name") or ""
                                if ftype not in ["hidden", "submit", "button"] and fname:
                                    field_names.append(fname)
                            
                            if len(field_names) >= 2:
                                print(f"[IFRAME] Found {len(field_names)} form fields in iframe")
                                self.page = frame
                                return
                            else:
                                print(f"[IFRAME] Skipping iframe with only {len(field_names)} fields")
        except Exception as e:
            print(f"[IFRAME] Error handling iframes: {e}")
    
    async def _analyze_fields(self, page_source: str, url: str) -> List[Dict]:
        """Analisis semua fields di form"""
        # First try platform-specific detection
        fields = await self._detect_fields_by_selector()
        
        if not fields:
            # Fallback to AI analysis
            fields = self.ai_analyzer.analyze_form_fields(page_source, url)
        
        return fields if fields else []
    
    async def _detect_fields_by_selector(self) -> List[Dict]:
        """Detect fields menggunakan Playwright selectors"""
        fields = []
        
        try:
            # Find all input fields
            inputs = await self.page.query_selector_all("input, textarea, select")
            
            for input_el in inputs:
                field_type = await input_el.get_attribute("type") or "text"
                field_name = await input_el.get_attribute("name") or ""
                field_id = await input_el.get_attribute("id") or ""
                placeholder = await input_el.get_attribute("placeholder") or ""
                aria_label = await input_el.get_attribute("aria-label") or ""
                
                # Skip hidden and submit fields
                if field_type in ["hidden", "submit", "button"]:
                    continue
                
                label = field_name or field_id or placeholder or aria_label
                
                if label:
                    fields.append({
                        "field_name": label,
                        "field_type": field_type,
                        "selector": f"input[name='{field_name}']" if field_name else f"#{field_id}" if field_id else None,
                        "options": [],
                        "required": await input_el.get_attribute("required") is not None,
                    })
            
            # Find all select elements
            selects = await self.page.query_selector_all("select")
            for select in selects:
                name = await select.get_attribute("name") or await select.get_attribute("id") or ""
                options = await select.query_selector_all("option")
                option_texts = []
                for opt in options:
                    text = await opt.text_content()
                    if text:
                        option_texts.append(text.strip())
                
                if name:
                    fields.append({
                        "field_name": name,
                        "field_type": "select",
                        "selector": f"select[name='{name}']",
                        "options": option_texts,
                        "required": await select.get_attribute("required") is not None,
                    })
            
            # Find all textareas
            textareas = await self.page.query_selector_all("textarea")
            for textarea in textareas:
                name = await textarea.get_attribute("name") or await textarea.get_attribute("id") or ""
                if name:
                    fields.append({
                        "field_name": name,
                        "field_type": "textarea",
                        "selector": f"textarea[name='{name}']",
                        "options": [],
                        "required": await textarea.get_attribute("required") is not None,
                    })
        
        except Exception as e:
            print(f"[FIELD DETECTION ERROR] {e}")
        
        return fields
    
    async def _fill_field(self, field: Dict, cv_path: str = None) -> bool:
        """Isi satu field"""
        field_name = field.get("field_name", "")
        field_type = field.get("field_type", "text")
        selector = field.get("selector")
        
        if not selector:
            return False
        
        try:
            element = await self.page.query_selector(selector)
            if not element:
                # Try alternative selectors
                element = await self._find_element_alternatives(field)
            
            if not element:
                print(f"  [SKIP] Cannot find: {field_name}")
                return False
            
            # Get value to fill
            value = self._get_field_value(field_name, field_type, field.get("options", []))
            
            if value is None:
                print(f"  [SKIP] No value for: {field_name}")
                return False
            
            # Fill based on type
            if field_type == "select":
                await self._fill_select(element, value, field.get("options", []))
            elif field_type == "checkbox":
                if value:
                    await element.check()
            elif field_type == "radio":
                await element.click()
            elif field_type == "file":
                if cv_path and os.path.exists(cv_path):
                    await element.set_input_files(cv_path)
            else:
                await element.click()
                await element.fill("")
                await element.type(str(value), delay=random.randint(30, 80))
            
            print(f"  [FILLED] {field_name}: {str(value)[:50]}...")
            return True
            
        except Exception as e:
            print(f"  [ERROR] {field_name}: {e}")
            return False
    
    async def _fill_select(self, element, value: str, options: List[str]):
        """Isi dropdown select"""
        # Try to select by value first
        try:
            await element.select_option(value=value)
            return
        except:
            pass
        
        # Try to select by label
        try:
            await element.select_option(label=value)
            return
        except:
            pass
        
        # Try AI to find best match
        if options:
            best = await self.ai_analyzer.select_best_option(
                element.get_attribute("name") or "", 
                options
            )
            try:
                await element.select_option(label=best)
                return
            except:
                pass
    
    async def _find_element_alternatives(self, field: Dict):
        """Cari element dengan alternative selectors"""
        field_name = field.get("field_name", "")
        
        alternatives = [
            f"[name='{field_name}']",
            f"[id='{field_name}']",
            f"[placeholder='{field_name}']",
            f"[aria-label='{field_name}']",
            f"label:has-text('{field_name}') + input",
            f"label:has-text('{field_name}') + textarea",
        ]
        
        for alt in alternatives:
            try:
                el = await self.page.query_selector(alt)
                if el:
                    return el
            except:
                continue
        
        return None
    
    def _get_field_value(self, field_name: str, field_type: str, 
                          options: List[str] = None) -> Any:
        """Get value untuk field berdasarkan profile"""
        personal = self.config.personal
        mappings = self.config.field_mappings
        
        # Map field name to profile attribute
        attr_name = mappings.get(field_name.lower().replace(" ", "_").replace("-", "_"))
        
        if attr_name and hasattr(personal, attr_name):
            value = getattr(personal, attr_name)
            
            # Handle list values
            if isinstance(value, list):
                if field_type == "checkbox":
                    return True  # Will be handled specially
                return ", ".join(str(v) for v in value[:5])
            return value
        
        # AI-assisted for custom questions
        if "?" in field_name or field_type == "textarea":
            return None  # Will be handled by AI in form_filler
        
        # Check if it's a common field
        common_fields = {
            "first_name": personal.first_name,
            "last_name": personal.last_name,
            "email": personal.email,
            "phone": personal.phone,
            "linkedin": personal.linkedin,
            "github": personal.github,
            "portfolio": personal.portfolio,
            "location": personal.location,
            "city": personal.city,
            "country": personal.country,
            "website": personal.portfolio,
        }
        
        return common_fields.get(field_name.lower())
    
    async def _submit_form(self, strategy: Dict) -> bool:
        """Submit form"""
        try:
            submit_selector = strategy.get("submit_selector")
            
            if submit_selector:
                submit_btn = await self.page.query_selector(submit_selector)
                if submit_btn:
                    await submit_btn.click()
                    await asyncio.sleep(2)
                    return True
            
            # Try common submit selectors
            common_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                "button:has-text('Submit')",
                "button:has-text('Apply')",
                "button:has-text('Send')",
                "a:has-text('Submit')",
            ]
            
            for selector in common_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(2)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"[SUBMIT ERROR] {e}")
            return False
    
    async def _random_delay(self):
        """Random delay untuk anti-detection"""
        if self.config.random_delay:
            delay = random.uniform(self.config.min_delay, self.config.max_delay)
            await asyncio.sleep(delay)
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        return random.choice(user_agents)
    
    def _log_submission(self, result: Dict):
        """Log submission"""
        self.submissions.append(result)
        
        os.makedirs(os.path.dirname(self.config.submissions_log), exist_ok=True)
        with open(self.config.submissions_log, 'w') as f:
            json.dump(self.submissions, f, indent=2, ensure_ascii=False)
    
    def get_stats(self) -> Dict:
        """Get submission statistics"""
        total = len(self.submissions)
        submitted = sum(1 for s in self.submissions if s.get("status") == "submitted")
        failed = sum(1 for s in self.submissions if s.get("status") in ["error", "submit_failed"])
        blocked = sum(1 for s in self.submissions if s.get("status") == "captcha_blocked")
        
        platforms = {}
        for s in self.submissions:
            p = s.get("platform", "unknown")
            platforms[p] = platforms.get(p, 0) + 1
        
        return {
            "total": total,
            "submitted": submitted,
            "failed": failed,
            "blocked": blocked,
            "success_rate": (submitted / total * 100) if total > 0 else 0,
            "platforms": platforms,
        }
