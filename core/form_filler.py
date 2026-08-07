"""
FORM FILLER - Isi form secara otomatis menggunakan Playwright
Handles semua jenis form: text, dropdown, checkbox, file upload, dll
"""
import asyncio
import json
import os
import random
import re
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import parse_qs, urlparse

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
                                dry_run: bool = False, company: str = "") -> Dict:
        """Main method: Isi application form di URL"""
        url = self._normalize_application_url(url, company)
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
        
        captcha_start_time = None
        
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
            
            # Check for CAPTCHA - hanya deteksi challenge DOM yang nyata
            captcha_info = await self._detect_captcha_dom()
            result["captcha_detected"] = captcha_info["has_captcha"]
            
            if captcha_info["has_captcha"]:
                captcha_start_time = time.time()
                print(f"[WARNING] Real CAPTCHA detected: {captcha_info['captcha_types']}")
                result["captcha_types"] = captcha_info["captcha_types"]
            
            # Extract job context for better answers
            job_context = self.ai_analyzer.extract_job_context(page_source, url)
            self._last_job_context = job_context
            print(f"[CONTEXT] Job context extracted")
            
            # Analyze form fields
            fields = await self._analyze_fields(page_source, url)
            print(f"[FIELDS] Found {len(fields)} form fields")
            
            # Jika CAPTCHA terdeteksi dan tidak ada field sama sekali, kemungkinan besar
            # CAPTCHA memblokir form. Tunggu sebentar lalu cek lagi.
            if captcha_start_time and len(fields) == 0:
                print(f"[CAPTCHA] No fields found with CAPTCHA present, waiting for possible challenge resolution...")
                for wait_attempt in range(3):
                    await self.page.wait_for_timeout(5000)
                    elapsed = time.time() - captcha_start_time
                    if elapsed >= self.config.captcha_skip_timeout:
                        result["status"] = "captcha_stuck"
                        result["captcha_skip_reason"] = f"No fields found after {int(elapsed)}s with CAPTCHA"
                        print(f"[CAPTCHA SKIP] Stuck for {int(elapsed)}s with no fields - SKIPPING")
                        self._log_submission(result)
                        return result
                    # Re-check fields
                    page_source = await self.page.content()
                    fields = await self._analyze_fields(page_source, url)
                    if fields:
                        print(f"[CAPTCHA] Fields appeared after {int(elapsed)}s wait")
                        break
            
            # Fill each field - dengan timeout check untuk CAPTCHA
            for field in fields:
                # Cek CAPTCHA timeout sebelum setiap field
                if captcha_start_time:
                    elapsed = time.time() - captcha_start_time
                    if elapsed >= self.config.captcha_skip_timeout:
                        result["status"] = "captcha_stuck"
                        result["captcha_skip_reason"] = f"Stuck filling fields for {int(elapsed)}s with CAPTCHA"
                        print(f"[CAPTCHA SKIP] Stuck for {int(elapsed)}s - SKIPPING remaining fields")
                        self._log_submission(result)
                        return result
                
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
            
            # Submit jika bukan dry run dan ada field yang terisi
            if not dry_run and result["fields_filled"] > 0:
                # Re-check CAPTCHA nyata tepat sebelum submit
                captcha_now = await self._detect_captcha_dom()
                if captcha_now["has_captcha"]:
                    result["status"] = "captcha_blocked"
                    result["captcha_skip_reason"] = "Real CAPTCHA challenge present - cannot submit"
                    print(f"[CAPTCHA BLOCK] {result['captcha_skip_reason']}: {captcha_now['captcha_types']}")
                else:
                    # Cek CAPTCHA timeout sebelum submit
                    if captcha_start_time:
                        elapsed = time.time() - captcha_start_time
                        if elapsed >= self.config.captcha_skip_timeout:
                            result["status"] = "captcha_stuck"
                            result["captcha_skip_reason"] = f"Stuck before submit for {int(elapsed)}s with CAPTCHA"
                            print(f"[CAPTCHA SKIP] Stuck for {int(elapsed)}s before submit - SKIPPING")
                            self._log_submission(result)
                            return result
                    
                    submit_result = await self._submit_form(strategy)
                    if submit_result.get("verified"):
                        result["status"] = "submitted"
                    elif submit_result.get("error"):
                        result["status"] = "submit_failed"
                        result["errors"].append(submit_result["error"])
                    else:
                        result["status"] = "submit_unverified"
            else:
                result["status"] = "dry_run" if dry_run else "filled_not_submitted"
            
            print(f"\n[RESULT] Status: {result['status']}")
            print(f"[RESULT] Fields filled: {result['fields_filled']}")
            print(f"[RESULT] Fields skipped: {result['fields_skipped']}")
            print(f"[RESULT] Custom questions: {result['custom_questions']}")
            
        except Exception as e:
            # Jika exception terjadi saat CAPTCHA aktif, cek apakah sudah timeout
            if captcha_start_time:
                elapsed = time.time() - captcha_start_time
                if elapsed >= self.config.captcha_skip_timeout:
                    result["status"] = "captcha_stuck"
                    result["captcha_skip_reason"] = f"Exception after {int(elapsed)}s with CAPTCHA: {str(e)}"
                    print(f"[CAPTCHA SKIP] Exception after {int(elapsed)}s with CAPTCHA - SKIPPING")
                    self._log_submission(result)
                    return result
            result["status"] = "error"
            result["errors"].append(str(e))
            print(f"[ERROR] {e}")
        
        self._log_submission(result)
        return result
    
    def _normalize_application_url(self, url: str, company: str = "") -> str:
        """Rewrite URL halaman marketing ke halaman form native ATS.
        
        Masalah utama bot: halaman marketing (mis. www.coinbase.com/careers/positions/ID?gh_jid=ID)
        membungkus form Greenhouse di dalam iframe/modal yang sering gagal dideteksi.
        Solusi: arahkan browser langsung ke form embed Greenhouse yang menampilkan form asli.
        """
        lowered = url.lower()
        
        # Sudah native greenhouse - tidak perlu diubah
        if "greenhouse.io" in lowered:
            return url
        
        # Ekstrak job id dari query gh_jid
        job_id = ""
        try:
            qs = parse_qs(urlparse(url).query)
            if qs.get("gh_jid"):
                job_id = qs["gh_jid"][0]
        except Exception:
            pass
        if not job_id:
            m = re.search(r"/(?:positions|jobs)/(\d+)", url)
            if m:
                job_id = m.group(1)
        
        if not job_id:
            return url
        
        co = (company or "").strip().lower()
        if not co:
            try:
                netloc = urlparse(url).netloc.lower().replace("www.", "")
                parts = netloc.split(".")
                co = parts[-2] if len(parts) >= 2 else parts[0]
            except Exception:
                co = ""
        if not co:
            return url
        
        embed = f"https://boards.greenhouse.io/embed/job_app?for={co}&token={job_id}"
        print(f"[URL] Rewritten: {url}\n      -> {embed}")
        return embed
    
    async def _detect_captcha_dom(self) -> Dict:
        """Deteksi CAPTCHA dari elemen DOM sungguhan (bukan string scan).
        Hanya lapor captcha jika ada widget/iframe challenge yang nyata,
        sehingga tidak terjadi false-positive seperti sebelumnya."""
        selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='turnstile']",
            "iframe[src*='challenge']",
            ".g-recaptcha",
            ".h-captcha",
            ".cf-turnstile",
            "div[data-sitekey]",
            "input[name='g-recaptcha-response']",
            "input[name='h-captcha-response']",
            "textarea[name='g-recaptcha-response']",
        ]
        found = []
        try:
            for sel in selectors:
                el = await self.page.query_selector(sel)
                if el:
                    found.append(sel)
                    if "recaptcha" in sel:
                        found.append("recaptcha")
                    elif "hcaptcha" in sel:
                        found.append("hcaptcha")
                    elif "turnstile" in sel:
                        found.append("turnstile")
                    else:
                        found.append("captcha")
        except Exception:
            pass
        
        # Cek teks challenge yang umum di halaman
        if not found:
            try:
                txt = await self.page.evaluate("document.body ? document.body.innerText : ''")
                low = (txt or "").lower()
                if ("verify you are human" in low or "i'm not a robot" in low
                        or "complete the captcha" in low or "captcha verification" in low):
                    found.append("captcha")
            except Exception:
                pass
        
        unique = sorted(set(found))
        has = len(unique) > 0
        if has:
            print(f"[CAPTCHA] Real challenge detected: {unique}")
        return {
            "has_captcha": has,
            "captcha_types": unique,
            "can_auto_solve": "turnstile" not in unique,
            "recommendation": "Skip (cannot solve)" if has else "Auto-fill possible",
        }
    
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
                form_indicators = [
                    "apply", "form", "application", "greenhouse", "lever", "ashby",
                    "job_app", "embed", "gh_jid", "boards",
                ]
                if any(ind in src or ind in name for ind in form_indicators):
                    print(f"[IFRAME] Found form iframe: {src[:80] or name}")
                    
                    # Try to switch to iframe
                    frame = await iframe.content_frame()
                    if frame:
                        # Wait for iframe content to load
                        try:
                            await frame.wait_for_load_state("domcontentloaded", timeout=10000)
                            await frame.wait_for_timeout(3000)
                        except:
                            pass
                        
                        # Check for form fields in iframe
                        inputs = await frame.query_selector_all("input, textarea, select")
                        if inputs:
                            # Verify it's not just a CAPTCHA widget inside
                            field_names = []
                            for inp in inputs[:15]:
                                ftype = await inp.get_attribute("type") or "text"
                                fname = await inp.get_attribute("name") or ""
                                if ftype not in ["hidden", "submit", "button"] and fname:
                                    field_names.append(fname)
                            
                            if len(field_names) >= 1:
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
                
                # Skip hidden, submit, button fields
                if field_type in ["hidden", "submit", "button"]:
                    continue
                
                # Skip numeric-only IDs (invalid CSS selectors)
                if field_id and field_id.isdigit():
                    field_id = ""
                
                label = field_name or field_id or placeholder or aria_label
                
                # Skip hidden tracking fields (bukan bagian form aplikasi)
                if label and self._is_tracking_field(label):
                    continue
                
                if label:
                    # Build safe selector
                    if field_name:
                        selector = f"input[name='{field_name}']"
                    elif field_id:
                        selector = f"#{field_id}"
                    else:
                        selector = None
                    
                    fields.append({
                        "field_name": label,
                        "field_type": field_type,
                        "selector": selector,
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
                
                if name and not self._is_tracking_field(name):
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
                if name and not self._is_tracking_field(name):
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
    
    def _is_tracking_field(self, field_name: str) -> bool:
        """Apakah field ini hanya tracking/marketing hidden field, bukan bagian form aplikasi."""
        n = field_name.lower().strip()
        if not n:
            return True
        
        patterns = [
            r"^ot[-_]group", r"vendor[-_]search", r"^chkbox",
            r"select[-_]all", r"-handler$", r"[-_]handler$",
            r"id[-_]c\d+$", r"-id[-_](?:c|group)\d*$",
            r"^g[-_]?recaptcha", r"^h[-_]?captcha", r"turnstile",
            r"^csrf", r"^_token", r"^fingerprint", r"^session", r"^device",
            r"^utm_", r"^fbclid", r"^gclid", r"^li_fat_id", r"^ga_",
            r"^sentry", r"^dd", r"^gtm", r"^analytics",
        ]
        for pat in patterns:
            if re.search(pat, n):
                return True
        return False
    
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
                element = await self._find_element_alternatives(field)
            
            if not element:
                print(f"  [SKIP] Cannot find: {field_name}")
                return False
            
            # Get value to fill
            value = self._get_field_value(field_name, field_type, field.get("options", []))
            
            # Handle file upload
            if field_type == "file":
                name_lower = field_name.lower()
                is_cover_letter = any(kw in name_lower for kw in [
                    "cover_letter", "coverletter", "cover letter",
                    "motivation", "motivational", "motivation_letter",
                    "cover_note", "covernote",
                ])
                
                if is_cover_letter:
                    # Cover letter file upload - skip (cannot generate PDF)
                    # Try AI text fallback if there's a nearby textarea
                    print(f"  [SKIP] Cover letter file upload (cannot generate PDF): {field_name}")
                    return False
                
                # Resume/CV upload
                file_path = cv_path or self._find_cv_file()
                if file_path and os.path.exists(file_path):
                    try:
                        await element.set_input_files(file_path)
                        print(f"  [UPLOAD] {os.path.basename(file_path)}")
                        return True
                    except Exception as e:
                        print(f"  [ERROR] Upload failed: {e}")
                        return False
                else:
                    print(f"  [SKIP] No CV file found for: {field_name}")
                    return False
            
            # Skip sensitive/demographic questions
            skip_patterns = [
                "gender", "pronouns", "ethnicity", "hispanic", "latino",
                "veteran", "disability", "disability_status",
                "race", "sexual_orientation", "marital",
                "gdpr_demographic", "g-recaptcha",
                "diversity", "demographic",
            ]
            name_lower = field_name.lower()
            if any(pat in name_lower for pat in skip_patterns):
                return False
            
            # Also check label text for sensitive questions
            if field_type == "textarea" or field_name.startswith("question_"):
                label = await self._get_question_label(element, field_name)
                if label:
                    label_lower = label.lower()
                    if any(pat in label_lower for pat in skip_patterns):
                        return False
            
            # AI generate jawaban untuk custom questions
            field_name_lower = field_name.lower()
            is_cover_letter_text = (
                value is None and field_type in ("textarea", "text") and (
                    "cover_letter" in field_name_lower or
                    "coverletter" in field_name_lower or
                    "cover letter" in field_name_lower or
                    "motivation" in field_name_lower or
                    "motivational" in field_name_lower
                )
            )
            is_custom_question = (
                value is None and not is_cover_letter_text and (
                    field_type == "textarea" or
                    "?" in field_name or
                    field_name.startswith("question_")
                )
            )
            
            if is_cover_letter_text:
                # Generate proper cover letter for cover letter fields
                question_text = await self._get_question_label(element, field_name)
                label = question_text or field_name
                print(f"  [AI] Generating cover letter for: {label[:60]}...")
                job_context = getattr(self, '_last_job_context', '')
                value = self.ai_analyzer.generate_cover_letter(job_context)
                if value and value != "N/A" and value != "Please fill manually":
                    print(f"  [AI] Cover letter generated ({len(value)} chars)")
                else:
                    print(f"  [SKIP] AI could not generate cover letter")
                    return False
            
            elif is_custom_question:
                question_text = await self._get_question_label(element, field_name)
                # Fallback: pakai field_name jika label tidak ditemukan
                if not question_text and (field_name.startswith("question_") or "?" in field_name):
                    question_text = field_name
                if question_text:
                    print(f"  [AI] Generating answer for: {question_text[:60]}...")
                    job_context = getattr(self, '_last_job_context', '')
                    value = self.ai_analyzer.generate_answer_for_question(question_text, job_context)
                    if value and value != "N/A" and value != "Please fill manually":
                        print(f"  [AI] Generated: {value[:80]}...")
                    else:
                        print(f"  [SKIP] AI could not generate answer for: {field_name}")
                        return False
                else:
                    return False
            
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
            elif field_type == "textarea":
                # Pakai fill() untuk textarea (lebih cepat dari type())
                await element.click()
                await element.fill(str(value)[:1000])
            else:
                await element.click()
                await element.fill("")
                await element.type(str(value)[:200], delay=random.randint(20, 50))
            
            print(f"  [FILLED] {field_name}: {str(value)[:50]}...")
            return True
            
        except Exception as e:
            print(f"  [ERROR] {field_name}: {e}")
            return False
    
    async def _get_question_label(self, element, field_name: str) -> str:
        """Ambil teks pertanyaan dari label terdekat - optimized"""
        try:
            # Quick checks first
            placeholder = await element.get_attribute("placeholder") or ""
            if placeholder and "?" in placeholder:
                return placeholder
            
            aria_label = await element.get_attribute("aria-label") or ""
            if aria_label and "?" in aria_label:
                return aria_label
            
            # Check field type - only try hard for textareas and text inputs
            tag = await element.evaluate("el => el.tagName.toLowerCase()")
            field_type = await element.get_attribute("type") or "text"
            
            # Skip select/dropdown questions (Greenhouse style) - they need option matching, not text answers
            if tag == "select" or field_type == "select-one":
                return ""
            
            # For input fields, check if there's a visible label nearby
            field_id = await element.get_attribute("id") or ""
            if field_id:
                label = await self.page.query_selector(f"label[for='{field_id}']")
                if label:
                    text = await label.text_content()
                    if text and "?" in text:
                        return text.strip()
            
            # Parent search (4 levels up) - termasuk Greenhouse .label / .form-question
            label_text = await element.evaluate("""el => {
                let current = el.parentElement;
                for (let i = 0; i < 4; i++) {
                    if (!current) break;
                    const candidates = current.querySelectorAll(
                        'label, .label, .form-label, .field-label, .form-question, .question'
                    );
                    for (const lbl of candidates) {
                        const text = lbl.textContent.trim();
                        if (text && text.includes('?')) return text;
                    }
                    current = current.parentElement;
                }
                return '';
            }""")
            
            if label_text and "?" in label_text:
                return label_text
            
            return ""
        except:
            return ""
    
    def _find_cv_file(self) -> str:
        """Cari file CV/Resume di project"""
        possible_names = [
            "Muhammad_Dawam_CV.pdf",
            "CV.pdf",
            "Resume.pdf",
            "muhammad_dawam_cv.pdf",
            "cv.pdf",
            "resume.pdf",
        ]
        
        base = os.path.dirname(os.path.dirname(__file__))
        for name in possible_names:
            path = os.path.join(base, name)
            if os.path.exists(path):
                return path
        
        # Cari semua .pdf di root
        for f in os.listdir(base):
            if f.lower().endswith(".pdf") and ("cv" in f.lower() or "resume" in f.lower()):
                return os.path.join(base, f)
        
        return ""
    
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
        
        # AI-assisted for custom questions - hanya textarea dan text input
        # Skip select/dropdown (handled separately) dan field numeric
        is_textarea_or_input = field_type in ("textarea", "text")
        is_custom = (
            is_textarea_or_input and (
                "?" in field_name or
                field_name.startswith("question_") or
                "cover_letter" in field_name.lower()
            )
        )
        if is_custom:
            return None  # Will be handled by AI in form_filler
        
        # Check if it's a common field
        common_fields = {
            "first_name": personal.first_name,
            "last_name": personal.last_name,
            "email": personal.email,
            "phone": personal.phone,
            "tel": personal.phone,
            "linkedin": personal.linkedin,
            "linkedin_url": personal.linkedin,
            "linkedin_profile": personal.linkedin,
            "profile_url": personal.linkedin,
            "github": personal.github,
            "github_url": personal.github,
            "portfolio": personal.portfolio,
            "website": personal.portfolio,
            "personal_website": personal.portfolio,
            "location": personal.location,
            "city": personal.city,
            "country": personal.country,
            "candidate_location": personal.location,
        }
        
        value = common_fields.get(field_name.lower())
        
        # Auto-add https:// for URL fields
        if value and field_type in ("url", "text") and any(
            kw in field_name.lower() for kw in ["url", "linkedin", "github", "website", "portfolio"]
        ):
            if value and not value.startswith("http"):
                value = "https://" + value
        
        return value
    
    async def _submit_form(self, strategy: Dict) -> Dict:
        """Submit form DAN verifikasi bahwa submit benar-benar diterima.
        Return: {"submitted": bool, "verified": bool, "error": str}
        Tidak lagi melaporkan sukses tanpa bukti."""
        url_before = self.page.url

        try:
            submit_selector = strategy.get("submit_selector")
            clicked = False

            if submit_selector:
                try:
                    submit_btn = await self.page.query_selector(submit_selector)
                    if submit_btn:
                        await submit_btn.click()
                        clicked = True
                except Exception:
                    pass

            if not clicked:
                common_selectors = [
                    "input[type='submit']",
                    "button[type='submit']",
                    "button:has-text('Submit Application')",
                    "button:has-text('Submit')",
                    "button:has-text('Apply')",
                    "button:has-text('Send')",
                    "a:has-text('Submit')",
                ]
                for selector in common_selectors:
                    try:
                        btn = await self.page.query_selector(selector)
                        if btn and await btn.is_visible():
                            await btn.click()
                            clicked = True
                            break
                    except:
                        continue

            if not clicked:
                return {"submitted": False, "verified": False, "error": "Submit button not found"}

            print("[SUBMIT] Button clicked, waiting for response...")
            await asyncio.sleep(3)
            return await self._verify_submission(url_before)

        except Exception as e:
            print(f"[SUBMIT ERROR] {e}")
            return {"submitted": False, "verified": False, "error": str(e)}

    async def _verify_submission(self, url_before: str) -> Dict:
        """Verifikasi apakah submit benar-benar diterima oleh ATS.
        Cek: pesan sukses, pesan error, atau perubahan URL."""
        try:
            current_url = self.page.url
            body_text = ""
            try:
                body_text = (await self.page.evaluate(
                    "document.body ? document.body.innerText : ''"
                )) or ""
            except Exception:
                pass
            low = body_text.lower()

            success_markers = [
                "thank you", "thanks for applying", "application submitted",
                "application received", "your application has been",
                "successfully submitted", "we've received", "we received your",
                "application complete", "submitted!", "your submission",
                "we have received your application", "application sent",
            ]
            error_markers = [
                "there was a problem", "please fix", "is required",
                "required field", "please complete", "please correct",
                "an error occurred", "something went wrong", "try again",
                "recaptcha", "captcha", "not a robot", "complete the captcha",
            ]

            url_ok = any(m in current_url.lower() for m in [
                "thank", "success", "received", "confirmation",
            ])
            matched_success = next((m for m in success_markers if m in low), None)
            matched_error = next((m for m in error_markers if m in low), None)

            if matched_success or (url_ok and not matched_error):
                print(f"[VERIFY] Success confirmed: '{matched_success or 'URL change'}'")
                return {"submitted": True, "verified": True, "error": ""}
            if matched_error:
                print(f"[VERIFY] Error detected: '{matched_error}'")
                return {"submitted": False, "verified": False,
                        "error": f"Form rejected: {matched_error}"}

            print("[VERIFY] No clear success/error signal (URL unchanged)")
            return {"submitted": False, "verified": False,
                    "error": "Could not confirm submission (no success page)"}
        except Exception as e:
            return {"submitted": False, "verified": False, "error": str(e)}
    
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
        failed = sum(1 for s in self.submissions if s.get("status") in ["error", "submit_failed", "submit_unverified"])
        blocked = sum(1 for s in self.submissions if s.get("status") in ("captcha_blocked", "captcha_stuck"))
        
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
