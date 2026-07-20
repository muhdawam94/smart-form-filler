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
        """Generate jawaban untuk custom question"""
        p = self.config.personal
        
        prompt = f"""
You are {p.full_name}, a {p.desired_role} with {p.years_experience} years experience.
You're applying for a job at a company that works with blockchain/Web3.

Job context: {job_context}

Generate a concise, professional answer (2-3 sentences max) for this question:
"{question}"

Your answer should:
- Be specific and relevant
- Show enthusiasm for the role/company
- Highlight relevant experience
- Be professional but personable
- NOT be generic or copy-paste

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
                    # Try to extract JSON from response
                    try:
                        return json.loads(result)
                    except json.JSONDecodeError:
                        # Try to find JSON in response
                        json_match = re.search(r'\[[\s\S]*?\]', result)
                        if json_match:
                            return json.loads(json_match.group())
                        json_match = re.search(r'\{[\s\S]*?\}', result)
                        if json_match:
                            return json.loads(json_match.group())
                        return []
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
                    try:
                        return json.loads(result)
                    except json.JSONDecodeError:
                        return []
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
