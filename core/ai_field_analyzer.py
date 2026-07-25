"""
AI FIELD ANALYZER - Gunakan AI untuk analisis dan isi custom form fields
Ini adalah "otak" dari smart form filler
"""
import json
import re
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
        
        if GROQ_AVAILABLE and config.ai.groq_api_key:
            self.groq_client = Groq(api_key=config.ai.groq_api_key)
        
        if OPENAI_AVAILABLE and config.ai.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=config.ai.openai_api_key)
    
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
        """Call AI provider"""
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
            print(f"[AI ERROR] {e}")
            return [] if is_json else "N/A"
    
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
