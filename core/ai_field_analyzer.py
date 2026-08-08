"""
AI FIELD ANALYZER - Gunakan AI untuk analisis dan isi custom form fields
Ini adalah "otak" dari smart form filler
"""
import json
import re
import os
import time
from typing import Dict, List, Optional, Any

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AIFieldAnalyzer:
    """Analisis form fields menggunakan AI dan generate jawaban yang tepat"""
    
    def __init__(self, config):
        self.config = config
        self.groq_client = None
        self.openai_client = None
        self._groq_keys = []
        self._groq_key_index = 0
        self._groq_key_cooldowns = {}  # key_index -> cooldown_until timestamp
        self._groq_key_errors = {}     # key_index -> consecutive error count
        self._all_keys_exhausted_until = 0  # global cooldown when all keys exhausted
        self._last_env_check = 0       # timestamp of last .env check
        self._env_check_interval = 60  # check .env every 60 seconds
        self._low_key_warned = False   # avoid spamming telegram
        self._MAX_WAIT_PER_CALL = 20   # budget nunggu cooldown per panggilan AI (detik)
        
        # Load keys initially
        self._load_keys_from_env()
        
        if GROQ_AVAILABLE and self._groq_keys:
            self.groq_client = Groq(api_key=self._groq_keys[0])
            print(f"  [AI] Loaded {len(self._groq_keys)} Groq API key(s)")
        
        if OPENAI_AVAILABLE and config.ai.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=config.ai.openai_api_key)
    
    def _load_keys_from_env(self):
        """Load API keys from .env file (supports hot-reload)"""
        # Re-read .env to pick up new keys without restart
        try:
            from dotenv import load_dotenv
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)
        except:
            pass
        
        keys_str = os.getenv("GROQ_API_KEYS", "") or os.getenv("GROQ_API_KEY", "")
        new_keys = [k.strip() for k in keys_str.split(",") if k.strip() and k.strip().startswith("gsk_")]
        
        # Detect new keys added
        old_count = len(self._groq_keys)
        if new_keys != self._groq_keys:
            self._groq_keys = new_keys
            if old_count > 0 and len(new_keys) > old_count:
                print(f"  [AI] New keys detected! {old_count} -> {len(new_keys)} keys")
                # Reset cooldowns for new keys
                self._groq_key_cooldowns = {}
                self._all_keys_exhausted_until = 0
                self._low_key_warned = False
                # Switch to first available key
                if self._groq_keys:
                    self._groq_key_index = 0
                    self.groq_client = Groq(api_key=self._groq_keys[0])
    
    def _maybe_reload_keys(self):
        """Periodically check .env for new keys"""
        now = time.time()
        if now - self._last_env_check >= self._env_check_interval:
            self._last_env_check = now
            self._load_keys_from_env()
    
    def _check_low_keys(self):
        """Send warning when keys are running low"""
        available = sum(1 for i in range(len(self._groq_keys))
                       if time.time() >= self._groq_key_cooldowns.get(i, 0))
        total = len(self._groq_keys)
        
        if total <= 1 and not self._low_key_warned:
            self._low_key_warned = True
            self._send_key_warning(
                f"AI keys: {total} total, {available} available.\n"
                f"Add more free keys at https://console.groq.com/keys\n"
                f"Then update GROQ_API_KEYS in .env (comma-separated)"
            )
        elif available == 0 and total > 0 and not self._low_key_warned:
            self._low_key_warned = True
            self._send_key_warning(
                f"All {total} AI keys on cooldown!\n"
                f"Bot will auto-retry when keys recover.\n"
                f"Add more free keys at https://console.groq.com/keys"
            )
    
    def _send_key_warning(self, message: str):
        """Send Telegram warning about key status"""
        try:
            import requests
            token = os.getenv("TELEGRAM_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            if token and chat_id:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": f"AI Key Warning:\n{message}",
                    },
                    timeout=5,
                )
        except:
            pass
    
    def _get_available_key_index(self) -> Optional[int]:
        """Find a key that's not on cooldown"""
        now = time.time()
        # Check if global cooldown active
        if now < self._all_keys_exhausted_until:
            return None
        # Find a key not on individual cooldown
        for i in range(len(self._groq_keys)):
            cooldown = self._groq_key_cooldowns.get(i, 0)
            if now >= cooldown:
                return i
        return None
    
    def _rotate_groq_key(self, failed_index: int):
        """Mark a key as failed and switch to next available"""
        # Track consecutive errors per key
        errors = self._groq_key_errors.get(failed_index, 0) + 1
        self._groq_key_errors[failed_index] = errors
        
        # Exponential backoff: 30s, 60s, 120s, 240s (max 5 min)
        cooldown = min(30 * (2 ** (errors - 1)), 300)
        self._groq_key_cooldowns[failed_index] = time.time() + cooldown
        print(f"  [AI] Key #{failed_index + 1} rate limited (error #{errors}), cooldown {cooldown}s")
        
        # Find next available key
        next_index = self._get_available_key_index()
        if next_index is not None and next_index != failed_index:
            self._groq_key_index = next_index
            self.groq_client = Groq(api_key=self._groq_keys[next_index])
            print(f"  [AI] Switched to key #{next_index + 1}/{len(self._groq_keys)}")
            self._check_low_keys()
            return True
        
        # All keys exhausted - set global cooldown (120s base, increases with errors)
        total_errors = sum(self._groq_key_errors.values())
        global_cooldown = min(120 + (total_errors * 30), 600)  # max 10 min
        self._all_keys_exhausted_until = time.time() + global_cooldown
        print(f"  [AI] ALL {len(self._groq_keys)} keys exhausted, global cooldown {global_cooldown}s")
        self._check_low_keys()
        return False
    
    def _get_profile_summary(self) -> str:
        """Get profile summary from config"""
        p = self.config.personal
        skills_str = ", ".join(p.skills[:10]) if p.skills else "Web3, DeFi, Python, JavaScript"
        return f"""
   - Name: {p.full_name}
   - Email: {p.email}
   - Phone: {p.phone}
   - LinkedIn: {p.linkedin}
   - GitHub: {p.github}
   - Portfolio: {p.portfolio}
   - Location: {p.location}
   - Role: {p.desired_role}
   - Experience: {p.years_experience} years
   - Skills: {skills_str}
   - Work: {p.work_type}, {p.expected_salary}, {p.availability}
   - Education: {p.education}
   - Languages: {', '.join(p.languages)}
   - Work Authorization: {p.authorized_to_work}, {p.requires_sponsorship} sponsorship
"""
    
    def analyze_form_fields(self, page_source: str, url: str = "") -> List[Dict]:
        """Analisis semua fields di form dan tentukan cara mengisinya"""
        profile = self._get_profile_summary()
        
        prompt = f"""
Analyze this job application form HTML and extract ALL form fields.

For each field, provide:
1. field_name: The name/id/label of the field
2. field_type: text, email, phone, select, textarea, file, checkbox, radio, url, number, date
3. required: true/false
4. options: list of options (for select/radio/checkbox), empty for others
5. suggested_value: What value to fill based on this profile:
{profile}
Return as JSON array.
If the form has custom questions (e.g., "Why do you want to work here?"), use AI to generate a good answer.

HTML (first 5000 chars):
{page_source[:5000]}
"""
        return self._call_ai(prompt, is_json=True)
    
    def generate_cover_letter(self, job_context: str = "") -> str:
        """Generate cover letter untuk application form"""
        p = self.config.personal
        skills_str = ", ".join(p.skills[:8]) if p.skills else "Web3, Marketing, Community Management"
        
        prompt = f"""
You are {p.full_name}, a {p.desired_role} with {p.years_experience} years of experience.

Your profile:
- Skills: {skills_str}
- Location: {p.location}
- Work preference: {p.work_type}

Job context: {job_context}

Write a professional cover letter (3-4 paragraphs, ~150 words) for this job application.
Structure:
1. Opening: Express enthusiasm for the role
2. Body: Highlight relevant experience and skills that match the job
3. Closing: Express eagerness to contribute and availability

Make it specific to the job context. Be genuine and professional.
Cover Letter:"""
        return self._call_ai(prompt, is_json=False)
    
    def generate_answer_for_question(self, question: str, job_context: str = "") -> str:
        """Generate jawaban untuk custom question - optimized"""
        p = self.config.personal
        
        # Detect simple yes/no questions
        q_lower = question.lower()
        simple_yes_no = any(phrase in q_lower for phrase in [
            "are you", "do you", "have you", "will you", "can you",
            "authorized", "sponsorship", "legally", "require visa",
        ])
        
        # Simple profile-based answers for yes/no questions
        if simple_yes_no:
            if "authorized" in q_lower or "legally" in q_lower:
                return p.authorized_to_work
            if "sponsorship" in q_lower or "visa" in q_lower:
                return p.requires_sponsorship
            if "willing" in q_lower and "office" in q_lower:
                return "Yes, I am willing to work from the specified office location."
            if "relationship" in q_lower:
                return "No, I do not have any personal or familial relationships with current Robinhood employees."
            return "Yes"
        
        prompt = f"""
You are {p.full_name}, a {p.desired_role} with {p.years_experience} years experience.

Job context: {job_context}

Answer this job application question in 1-2 sentences (max 50 words):
"{question}"

Be specific and professional. Do NOT be generic.
Answer:"""
        return self._call_ai(prompt, is_json=False)
    
    def select_best_option(self, field_name: str, options: List[str], field_context: str = "") -> str:
        """Pilih option terbaik untuk dropdown/radio"""
        p = self.config.personal
        
        prompt = f"""
Given a form field "{field_name}" with these options: {json.dumps(options)}

Context: {field_context}
Profile: {p.full_name}, {p.desired_role}, {p.location}, {p.years_experience} years experience

Select the BEST matching option. Return ONLY the exact option text, nothing else.
If no good match, return the most general/default option.
"""
        result = self._call_ai(prompt, is_json=False)
        return result.strip().strip('"').strip("'")
    
    def handle_checkbox_group(self, field_name: str, options: List[str], 
                              selected_count: int = 0) -> List[str]:
        """Tentukan checkbox mana yang harus dicentang"""
        p = self.config.personal
        skills_str = ", ".join(p.skills) if p.skills else "Python, JavaScript, TypeScript, React, Web3, DeFi"
        
        prompt = f"""
Field: {field_name}
Options: {json.dumps(options)}
Max selections needed: {selected_count if selected_count > 0 else 'all relevant'}

Profile: {p.full_name} - {skills_str}

Select the checkboxes that match the profile. Return as JSON array of selected options.
Only return options that are genuinely relevant.
"""
        return self._call_ai(prompt, is_json=True)
    
    def detect_captcha(self, page_source: str) -> Dict:
        """Deteksi apakah ada CAPTCHA di form"""
        captcha_patterns = {
            "recaptcha": ["recaptcha", "g-recaptcha", "google.com/recaptcha"],
            "hcaptcha": ["hcaptcha", "h-captcha"],
            "turnstile": ["turnstile", "cloudflare-turnstile"],
            "captcha": ["captcha", "verify you are human"],
        }
        
        source_lower = page_source.lower()
        detected = []
        
        for captcha_type, patterns in captcha_patterns.items():
            for pattern in patterns:
                if pattern in source_lower:
                    detected.append(captcha_type)
                    break
        
        return {
            "has_captcha": len(detected) > 0,
            "captcha_types": detected,
            "can_auto_solve": "turnstile" not in detected,  # Turnstile hard to bypass
            "recommendation": "Skip or manual intervention" if detected else "Auto-fill possible"
        }
    
    def extract_job_context(self, page_source: str, url: str = "") -> str:
        """Extract job context dari page untuk generate jawaban yang lebih baik"""
        prompt = f"""
Extract job context from this job posting page:
URL: {url}

Return a brief summary (2-3 sentences) including:
1. Job title
2. Company name (if visible)
3. Key requirements
4. Tech stack mentioned

HTML: {page_source[:3000]}

Return as plain text summary:"""
        return self._call_ai(prompt, is_json=False)
    
    def _call_ai(self, prompt: str, is_json: bool = False) -> Any:
        """Call AI provider with automatic key rotation on 429
        
        Bot never stops - always retries with available keys or waits for cooldown.
        Auto-reloads new keys from .env every 60s.
        """
        # Hot-reload keys from .env (picks up new keys without restart)
        self._maybe_reload_keys()
        
        max_attempts = max(len(self._groq_keys) * 2, 4)  # Try each key at least twice
        
        for attempt in range(max_attempts):
            # Wait if global cooldown active - tapi dibatasi budget kecil per call
            # supaya satu pertanyaan tidak menghentikan proses isi form berjam-jam.
            now = time.time()
            if now < self._all_keys_exhausted_until:
                wait = min(self._all_keys_exhausted_until - now, self._MAX_WAIT_PER_CALL)
                if wait > 0:
                    print(f"  [AI] All keys on cooldown, waiting up to {int(wait)}s (budget)...")
                    waited = 0
                    while waited < wait:
                        time.sleep(5)
                        waited += 5
                        self._maybe_reload_keys()
                        if self._get_available_key_index() is not None:
                            print(f"  [AI] Key available after wait!")
                            break
                    if self._get_available_key_index() is None:
                        print("  [AI] Keys still unavailable - using fallback for this call")
                        return [] if is_json else "Please fill manually"
                    continue
            
            try:
                # Try Groq first (free)
                if self.groq_client:
                    response = self.groq_client.chat.completions.create(
                        model=self.config.ai.groq_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7 if not is_json else 0.3,
                        max_tokens=1000,
                    )
                    result = response.choices[0].message.content.strip()
                    
                    if is_json:
                        return self._extract_json(result)
                    return result
                
                # Fallback to OpenAI
                if self.openai_client:
                    response = self.openai_client.chat.completions.create(
                        model=self.config.ai.openai_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7 if not is_json else 0.3,
                        max_tokens=1000,
                    )
                    result = response.choices[0].message.content.strip()
                    
                    if is_json:
                        return self._extract_json(result)
                    return result
                
                # No AI available - use basic heuristics
                return self._fallback_analysis(prompt, is_json)
                
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = any(kw in error_str for kw in [
                    "429", "rate", "limit", "quota", "too many requests",
                    "requests per", "tokens per",
                ])
                
                if is_rate_limit:
                    print(f"  [AI] Rate limited (attempt {attempt + 1}/{max_attempts})")
                    # Rotate to next key
                    if self._rotate_groq_key(self._groq_key_index):
                        time.sleep(1)  # Brief pause before retry
                        continue
                    else:
                        # All keys exhausted - short wait then retry (bot continues)
                        time.sleep(2)
                        continue
                else:
                    print(f"[AI ERROR] {e}")
                    return [] if is_json else "N/A"
        
        # After all attempts, return fallback (bot continues to next job)
        print(f"  [AI] Max attempts reached, using fallback")
        return [] if is_json else "Please fill manually"
    
    def _fallback_analysis(self, prompt: str, is_json: bool) -> Any:
        """Fallback analysis tanpa AI"""
        if is_json:
            return []
        return "Please fill manually"
    
    def _extract_json(self, text: str) -> Any:
        """Robust JSON extraction from AI response - handles markdown fences, partial JSON, etc."""
        if not text:
            return []
        
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Strip markdown code fences
        cleaned = re.sub(r'```(?:json)?\s*', '', text)
        cleaned = re.sub(r'```\s*$', '', cleaned.strip())
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # Try to find array [...]
        match = re.search(r'(\[[\s\S]*\])', cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                # Try fixing common issues: trailing commas, single quotes
                fixed = re.sub(r',\s*]', ']', match.group(1))
                fixed = fixed.replace("'", '"')
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
        
        # Try to find object {...}
        match = re.search(r'(\{[\s\S]*\})', cleaned)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        print(f"[AI] Could not parse JSON from response: {text[:200]}")
        return []
