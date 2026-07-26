"""
SMART FORM FILLER - Configuration
Config untuk smart form filler yang bisa handle semua jenis application forms

IMPORTANT: All personal data is loaded from .env file
Copy .env.example to .env and fill in your details
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

@dataclass
class PersonalInfo:
    """Data diri untuk auto-fill - loaded from .env"""
    full_name: str = os.getenv("FULL_NAME", "")
    first_name: str = os.getenv("FIRST_NAME", "")
    last_name: str = os.getenv("LAST_NAME", "")
    email: str = os.getenv("EMAIL", "")
    phone: str = os.getenv("PHONE", "")
    linkedin: str = os.getenv("LINKEDIN", "")
    github: str = os.getenv("GITHUB", "")
    portfolio: str = os.getenv("PORTFOLIO", "")
    location: str = os.getenv("LOCATION", "")
    city: str = os.getenv("CITY", "")
    country: str = os.getenv("COUNTRY", "")
    timezone: str = os.getenv("TIMEZONE", "UTC+7 (WIB)")
    
    # Work preferences
    desired_role: str = os.getenv("DESIRED_ROLE", "Web3 Developer / DeFi Engineer")
    work_type: str = os.getenv("WORK_TYPE", "Remote / Contract")
    expected_salary: str = os.getenv("EXPECTED_SALARY", "30-50 USD/hour")
    availability: str = os.getenv("AVAILABILITY", "Immediately")
    start_date: str = os.getenv("START_DATE", "Immediately")
    
    # Experience
    years_experience: str = os.getenv("YEARS_EXPERIENCE", "7+")
    education: str = os.getenv("EDUCATION", "Bachelor's Degree")
    
    # Skills (untuk dropdown/checkbox forms)
    skills: List[str] = field(default_factory=lambda: os.getenv("SKILLS", 
        "Python,JavaScript,TypeScript,React,Next.js,Node.js,Solidity,Rust,Solana,Anchor,Web3,DeFi,Smart Contracts,REST API,GraphQL,PostgreSQL,MongoDB,Docker,AWS,Git,UI/UX Design,Figma,Tailwind CSS,HTML/CSS"
    ).split(","))
    
    # Languages
    languages: List[str] = field(default_factory=lambda: os.getenv("LANGUAGES",
        "Indonesian (Native),English (Conversational)"
    ).split(","))
    
    # Work authorization
    authorized_to_work: str = os.getenv("AUTHORIZED_TO_WORK", "Yes, remote/contract")
    requires_sponsorship: str = os.getenv("REQUIRES_SPONSORSHIP", "No")
    visa_status: str = os.getenv("VISA_STATUS", "N/A - Remote work")

@dataclass
class AIConfig:
    """AI configuration untuk smart form filling"""
    provider: str = "groq"  # groq (free), openai, anthropic
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = "llama-3.1-8b-instant"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = "claude-3-haiku-20240307"

@dataclass
class FormFillerConfig:
    """Main configuration"""
    personal: PersonalInfo = field(default_factory=PersonalInfo)
    ai: AIConfig = field(default_factory=AIConfig)
    
    # Browser settings
    headless: bool = False  # False = show browser (untuk debugging)
    slow_mo: int = 500  # Delay antar action (ms)
    timeout: int = 60000  # Page timeout (ms) - 60 detik
    
    # CAPTCHA handling
    captcha_skip_timeout: int = 180  # Skip job jika CAPTCHA stuck > 3 menit (detik)
    captcha_check_interval: int = 5  # Interval cek CAPTCHA (detik)
    
    # Anti-detection
    random_delay: bool = True
    min_delay: int = 1
    max_delay: int = 3
    
    # Database
    db_path: str = "data/form_templates.db"
    submissions_log: str = "data/submissions.json"
    cv_path: str = os.getenv("CV_PATH", "")  # Path ke file CV/Resume (PDF)
    
    # Platforms to handle
    known_platforms: List[str] = field(default_factory=lambda: [
        "greenhouse", "lever", "ashby", "workday", "smartrecruiters",
        "bamboohr", "breezyhr", "workable", "jazzhr", "jobvite",
        "icims", "successfactors", "taleo", "ukg", "paycom",
        "custom", "unknown"
    ])
    
    # Common field mappings (field_name -> profile_value)
    field_mappings: Dict[str, str] = field(default_factory=lambda: {
        # Name fields
        "first_name": "first_name",
        "last_name": "last_name",
        "full_name": "full_name",
        "name": "full_name",
        
        # Contact
        "email": "email",
        "phone": "phone",
        "phone_number": "phone",
        "mobile": "phone",
        "tel": "phone",
        "linkedin": "linkedin",
        "linkedin_url": "linkedin",
        "linkedin_profile": "linkedin",
        "profile_url": "linkedin",
        "github": "github",
        "github_url": "github",
        "portfolio": "portfolio",
        "website": "portfolio",
        "personal_website": "portfolio",
        "url": "portfolio",
        "candidate_location": "location",
        
        # Location
        "location": "location",
        "city": "city",
        "country": "country",
        "address": "location",
        
        # Work
        "desired_role": "desired_role",
        "position": "desired_role",
        "role": "desired_role",
        "work_type": "work_type",
        "employment_type": "work_type",
        "availability": "availability",
        "start_date": "start_date",
        "expected_salary": "expected_salary",
        "salary": "expected_salary",
        "compensation": "expected_salary",
        
        # Experience
        "years_experience": "years_experience",
        "experience": "years_experience",
        
        # Authorization
        "authorized_to_work": "authorized_to_work",
        "work_authorization": "authorized_to_work",
        "requires_sponsorship": "requires_sponsorship",
        "sponsorship": "requires_sponsorship",
        "visa_status": "visa_status",
        "right_to_work": "authorized_to_work",
        
        # Education
        "education": "education",
        "degree": "education",
        
        # Skills
        "skills": "skills",
        "technologies": "skills",
        "programming_languages": "skills",
    })

def get_config() -> FormFillerConfig:
    """Get singleton config instance"""
    return FormFillerConfig()
