"""
PLATFORM DETECTOR - Deteksi ATS/Platform yang digunakan
Menganalisis URL, page source, dan DOM elements untuk identifikasi platform
"""
import re
from urllib.parse import urlparse
from typing import Optional, Dict, List

class PlatformDetector:
    """DeteksiATS/Platform otomatis dari URL dan page content"""
    
    # Platform signatures (pattern -> platform_name)
    SIGNATURES = {
        # Greenhouse
        "greenhouse": {
            "url_patterns": ["greenhouse.io", "boards.greenhouse.io"],
            "dom_selectors": [
                "#application_form",
                ".application-form",
                "input[name='job_application[location]']",
                "div.greenhouse",
            ],
            "meta_patterns": ["greenhouse"],
            "form_action_patterns": ["greenhouse.io"],
        },
        
        # Lever
        "lever": {
            "url_patterns": ["lever.co", "jobs.lever.co"],
            "dom_selectors": [
                ".application",
                "application-form",
                "input[name='name']",
                "div.lever",
            ],
            "meta_patterns": ["lever"],
            "form_action_patterns": ["lever.co"],
        },
        
        # Ashby
        "ashby": {
            "url_patterns": ["ashbyhq.com", "jobs.ashbyhq.com"],
            "dom_selectors": [
                "ashby-application-form",
                ".ashby-form",
                "div.ashby",
            ],
            "meta_patterns": ["ashby"],
            "form_action_patterns": ["ashbyhq.com"],
        },
        
        # Workday
        "workday": {
            "url_patterns": ["myworkdayjobs.com", "workday.com"],
            "dom_selectors": [
                "[data-automation-id]",
                ".WGAG",
                "div.workday",
            ],
            "meta_patterns": ["workday"],
            "form_action_patterns": ["myworkdayjobs.com"],
        },
        
        # SmartRecruiters
        "smartrecruiters": {
            "url_patterns": ["smartrecruiters.com"],
            "dom_selectors": [
                ".sr-application-form",
                "div.smartrecruiters",
                "#application-form",
            ],
            "meta_patterns": ["smartrecruiters"],
            "form_action_patterns": ["smartrecruiters.com"],
        },
        
        # BambooHR
        "bamboohr": {
            "url_patterns": ["bamboohr.com", "bamboo.hr"],
            "dom_selectors": [
                ".BambooHR-ATS-board",
                "div.bamboo",
            ],
            "meta_patterns": ["bamboohr"],
            "form_action_patterns": ["bamboohr.com"],
        },
        
        # BreezyHR
        "breezyhr": {
            "url_patterns": ["breezy.hr", "breezyhr.com"],
            "dom_selectors": [
                ".breezy-apply",
                "div.breezy",
            ],
            "meta_patterns": ["breezy"],
            "form_action_patterns": ["breezy.hr"],
        },
        
        # Workable
        "workable": {
            "url_patterns": ["workable.com"],
            "dom_selectors": [
                ".workable-application",
                "div.workable",
            ],
            "meta_patterns": ["workable"],
            "form_action_patterns": ["workable.com"],
        },
        
        # JazzHR
        "jazzhr": {
            "url_patterns": ["jazz.co", "jazzhr.com"],
            "dom_selectors": [
                ".jazz-application",
                "div.jazz",
            ],
            "meta_patterns": ["jazz"],
            "form_action_patterns": ["jazzhr.com"],
        },
        
        # Jobvite
        "jobvite": {
            "url_patterns": ["jobvite.com"],
            "dom_selectors": [
                ".jobvite-form",
                "div.jobvite",
            ],
            "meta_patterns": ["jobvite"],
            "form_action_patterns": ["jobvite.com"],
        },
        
        # iCIMS
        "icims": {
            "url_patterns": ["icims.com", "careers-"],
            "dom_selectors": [
                ".icims",
                "div.icims",
            ],
            "meta_patterns": ["icims"],
            "form_action_patterns": ["icims.com"],
        },
        
        # SuccessFactors
        "successfactors": {
            "url_patterns": ["successfactors.com", "sap.com"],
            "dom_selectors": [
                ".successfactors",
                "div.successfactors",
            ],
            "meta_patterns": ["successfactors"],
            "form_action_patterns": ["successfactors.com"],
        },
        
        # Taleo
        "taleo": {
            "url_patterns": ["taleo.net"],
            "dom_selectors": [
                ".taleo",
                "div.taleo",
            ],
            "meta_patterns": ["taleo"],
            "form_action_patterns": ["taleo.net"],
        },
    }
    
    def __init__(self):
        self.detected_history: Dict[str, str] = {}
    
    def detect_from_url(self, url: str) -> Optional[str]:
        """Deteksi platform dari URL"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        
        for platform, signatures in self.SIGNATURES.items():
            for pattern in signatures["url_patterns"]:
                if pattern in domain or pattern in path:
                    return platform
        
        return None
    
    def detect_from_page_source(self, page_source: str) -> Optional[str]:
        """Deteksi platform dari page source HTML"""
        source_lower = page_source.lower()
        
        for platform, signatures in self.SIGNATURES.items():
            # Check meta patterns
            for pattern in signatures["meta_patterns"]:
                if pattern in source_lower:
                    return platform
            
            # Check form action patterns
            for pattern in signatures["form_action_patterns"]:
                if pattern in source_lower:
                    return platform
        
        return None
    
    def detect_from_selectors(self, page_content: str) -> Optional[str]:
        """Deteksi platform dari DOM selectors yang ditemukan"""
        for platform, signatures in self.SIGNATURES.items():
            for selector in signatures["dom_selectors"]:
                # Simple check - actual implementation would use Playwright
                if selector.replace(".", "").replace("#", "") in page_content.lower():
                    return platform
        
        return None
    
    def detect(self, url: str = "", page_source: str = "") -> str:
        """Main detection - combine semua methods"""
        # Try URL first (most reliable)
        if url:
            result = self.detect_from_url(url)
            if result:
                self.detected_history[url] = result
                return result
        
        # Try page source
        if page_source:
            result = self.detect_from_page_source(page_source)
            if result:
                if url:
                    self.detected_history[url] = result
                return result
            
            result = self.detect_from_selectors(page_source)
            if result:
                if url:
                    self.detected_history[url] = result
                return result
        
        return "unknown"
    
    def get_form_strategy(self, platform: str) -> Dict:
        """Get strategy untuk mengisi form berdasarkan platform"""
        strategies = {
            "greenhouse": {
                "method": "sequential_fill",
                "submit_selector": "input[type='submit']",
                "has_captcha": False,
                "has_file_upload": True,
                "custom_questions": True,
                "estimated_time": "2-3 minutes",
                "success_rate": 0.95,
            },
            "lever": {
                "method": "sequential_fill",
                "submit_selector": "button[data-qa='btn-submit']",
                "has_captcha": False,
                "has_file_upload": True,
                "custom_questions": True,
                "estimated_time": "2-3 minutes",
                "success_rate": 0.93,
            },
            "ashby": {
                "method": "sequential_fill",
                "submit_selector": "button[type='submit']",
                "has_captcha": False,
                "has_file_upload": True,
                "custom_questions": True,
                "estimated_time": "2-4 minutes",
                "success_rate": 0.90,
            },
            "workday": {
                "method": "complex_form",
                "submit_selector": "[data-automation-id='bottom-buttons-next']",
                "has_captcha": True,
                "has_file_upload": True,
                "custom_questions": True,
                "estimated_time": "5-10 minutes",
                "success_rate": 0.75,
            },
            "smartrecruiters": {
                "method": "sequential_fill",
                "submit_selector": "button[type='submit']",
                "has_captcha": False,
                "has_file_upload": True,
                "custom_questions": True,
                "estimated_time": "2-3 minutes",
                "success_rate": 0.92,
            },
            "bamboohr": {
                "method": "sequential_fill",
                "submit_selector": "input[type='submit']",
                "has_captcha": False,
                "has_file_upload": True,
                "custom_questions": True,
                "estimated_time": "2-3 minutes",
                "success_rate": 0.91,
            },
            "custom": {
                "method": "ai_assisted",
                "submit_selector": None,  # Need AI to detect
                "has_captcha": True,  # Assume worst case
                "has_file_upload": True,
                "custom_questions": True,
                "estimated_time": "3-5 minutes",
                "success_rate": 0.70,
            },
            "unknown": {
                "method": "ai_assisted",
                "submit_selector": None,
                "has_captcha": True,
                "has_file_upload": True,
                "custom_questions": True,
                "estimated_time": "5-8 minutes",
                "success_rate": 0.60,
            },
        }
        
        return strategies.get(platform, strategies["unknown"])
    
    def get_supported_platforms(self) -> List[str]:
        """Return list semua supported platforms"""
        return list(self.SIGNATURES.keys()) + ["custom", "unknown"]
