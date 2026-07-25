"""
24/7 BOT SCHEDULER - Otomatis apply 15-20 kali sehari
Jalankan di cloud (GitHub Actions / Railway / Render) tanpa laptop nyala
"""
import os
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

class DailyScheduler:
    """Scheduler yang membatasi aplikasi per hari"""
    
    def __init__(self):
        self.config_file = "scheduler_config.json"
        self.state_file = "scheduler_state.json"
        self.load_config()
        self.load_state()
    
    def load_config(self):
        """Load konfigurasi scheduler"""
        default_config = {
            "max_applications_per_day": 18,  # 15-20, kita pakai 18
            "min_delay_between_apps": 300,  # 5 menit (detik)
            "max_delay_between_apps": 900,  # 15 menit (detik)
            "active_hours": {"start": 0, "end": 24},  # 24/7 (cron handles scheduling)
            "timezone_offset": 7,  # WIB = UTC+7
            "retry_failed": True,
            "max_retries": 2,
            "preferred_platforms": [
                "greenhouse", "lever", "ashby", "smartrecruiters", "bamboohr"
            ],
            "skip_platforms": ["workday"],  # Terlalu banyak CAPTCHA
            "daily_reset_hour": 0,  # Reset counter jam 00:00 UTC
        }
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Simpan konfigurasi"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def load_state(self):
        """Load state scheduler"""
        default_state = {
            "today_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "applications_today": 0,
            "total_applications": 0,
            "successful_applications": 0,
            "failed_applications": 0,
            "last_application_time": None,
            "applied_jobs": [],
            "daily_history": [],
        }
        
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
        else:
            self.state = default_state
            self.save_state()
    
    def save_state(self):
        """Simpan state"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def reset_daily_counter(self):
        """Reset counter harian"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        if self.state["today_date"] != today:
            # Simpan history kemarin
            if self.state["applications_today"] > 0:
                self.state["daily_history"].append({
                    "date": self.state["today_date"],
                    "applications": self.state["applications_today"],
                    "successful": self.state.get("daily_successful", 0),
                })
            
            # Reset
            self.state["today_date"] = today
            self.state["applications_today"] = 0
            self.state["daily_successful"] = 0
            self.save_state()
    
    def can_apply(self) -> dict:
        """Cek apakah masih boleh apply"""
        self.reset_daily_counter()
        
        now = datetime.utcnow()
        wib_hour = (now.hour + self.config["timezone_offset"]) % 24
        
        result = {
            "can_apply": True,
            "reason": "",
            "remaining_today": self.config["max_applications_per_day"] - self.state["applications_today"],
            "next_available_time": None,
        }
        
        # Cek jam aktif
        active_start = self.config["active_hours"]["start"]
        active_end = self.config["active_hours"]["end"]
        
        # Konversi ke WIB
        active_start_wib = (active_start + self.config["timezone_offset"]) % 24
        active_end_wib = (active_end + self.config["timezone_offset"]) % 24
        
        if active_start_wib <= wib_hour < active_end_wib:
            pass  # Dalam jam aktif
        else:
            result["can_apply"] = False
            result["reason"] = f"Saat ini jam {wib_hour}:00 WIB, di luar jam aktif ({active_start_wib}:00-{active_end_wib}:00 WIB)"
            # Hitung kapan bisa apply lagi
            if wib_hour < active_start_wib:
                hours_until = active_start_wib - wib_hour
            else:
                hours_until = 24 - wib_hour + active_start_wib
            result["next_available_time"] = (now + timedelta(hours=hours_until)).isoformat()
            return result
        
        # Cek kuota harian
        if self.state["applications_today"] >= self.config["max_applications_per_day"]:
            result["can_apply"] = False
            result["reason"] = f"Batas harian tercapai: {self.state['applications_today']}/{self.config['max_applications_per_day']}"
            result["next_available_time"] = (now + timedelta(days=1)).replace(hour=active_start).isoformat()
            return result
        
        # Cek delay antar aplikasi
        if self.state["last_application_time"]:
            last_time = datetime.fromisoformat(self.state["last_application_time"])
            elapsed = (now - last_time).total_seconds()
            min_delay = self.config["min_delay_between_apps"]
            
            if elapsed < min_delay:
                result["can_apply"] = False
                wait_time = min_delay - elapsed
                result["reason"] = f"Tunggu {int(wait_time/60)} menit lagi"
                result["next_available_time"] = (now + timedelta(seconds=wait_time)).isoformat()
                return result
        
        return result
    
    def record_application(self, job_url: str, platform: str, success: bool):
        """Record aplikasi yang sudah dikirim"""
        self.reset_daily_counter()
        
        self.state["applications_today"] += 1
        self.state["total_applications"] += 1
        self.state["last_application_time"] = datetime.utcnow().isoformat()
        
        if success:
            self.state["successful_applications"] += 1
            self.state["daily_successful"] = self.state.get("daily_successful", 0) + 1
        else:
            self.state["failed_applications"] += 1
        
        self.state["applied_jobs"].append({
            "url": job_url,
            "platform": platform,
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
        })
        
        # Keep last 30 days of history
        cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
        self.state["applied_jobs"] = [
            j for j in self.state["applied_jobs"]
            if j["timestamp"] > cutoff
        ]
        
        self.save_state()
    
    def get_next_delay(self) -> int:
        """Hitung delay berikutnya (detik)"""
        return random.randint(
            self.config["min_delay_between_apps"],
            self.config["max_delay_between_apps"]
        )
    
    def get_daily_stats(self) -> dict:
        """Get statistik hari ini"""
        return {
            "date": self.state["today_date"],
            "applied": self.state["applications_today"],
            "remaining": self.config["max_applications_per_day"] - self.state["applications_today"],
            "max": self.config["max_applications_per_day"],
            "total_all_time": self.state["total_applications"],
            "success_rate": (
                self.state["successful_applications"] / self.state["total_applications"] * 100
                if self.state["total_applications"] > 0 else 0
            ),
        }
    
    def get_schedule_display(self) -> str:
        """Tampilkan jadwal harian"""
        self.reset_daily_counter()
        
        now = datetime.utcnow()
        wib_hour = (now.hour + self.config["timezone_offset"]) % 24
        
        stats = self.get_daily_stats()
        
        schedule = f"""
====================================================
              24/7 BOT SCHEDULER STATUS
====================================================

  Waktu Sekarang: {wib_hour}:00 WIB ({now.strftime('%H:%M')} UTC)

  JADWAL HARI INI:
  ----------------
  Jam Aktif: 15:00 - 05:00 WIB (22:00-08:00 UTC)
  Max Aplikasi/Hari: {stats['max']}
  Sudah Apply: {stats['applied']}/{stats['max']}
  Sisa Kuota: {stats['remaining']}

  DELAY ANTAR APLIKASI:
  ---------------------
  Minimum: {self.config['min_delay_between_apps']//60} menit
  Maksimum: {self.config['max_delay_between_apps']//60} menit

  TOTAL STATISTIK:
  ----------------
  Total Apply: {stats['total_all_time']}
  Success Rate: {stats['success_rate']:.1f}%

  PLATFORM PRIORITAS:
  -------------------
  {', '.join(self.config['preferred_platforms'][:3])}

====================================================
"""
        return schedule


def create_github_actions_workflow():
    """Buat GitHub Actions workflow untuk 24/7 execution"""
    workflow = """
name: 24/7 Job Auto-Apply Bot

on:
  schedule:
    # Run setiap 30 menit dari jam 15:00-05:00 WIB (08:00-22:00 UTC)
    - cron: '0,30 8-21 * * *'  # Setiap 30 menit
    - cron: '0 22 * * *'       # Jam 22:00 UTC (05:00 WIB)
    - cron: '30 22 * * *'      # Jam 22:30 UTC
    - cron: '0 23 * * *'       # Jam 23:00 UTC
    - cron: '30 23 * * *'      # Jam 23:30 UTC
    - cron: '0 0 * * *'        # Jam 00:00 UTC
    - cron: '30 0 * * *'       # Jam 00:30 UTC
    - cron: '0 1 * * *'        # Jam 01:00 UTC
    - cron: '30 1 * * *'       # Jam 01:30 UTC
    - cron: '0 2 * * *'        # Jam 02:00 UTC
    - cron: '30 2 * * *'       # Jam 02:30 UTC
    - cron: '0 3 * * *'        # Jam 03:00 UTC
    - cron: '30 3 * * *'       # Jam 03:30 UTC
    - cron: '0 4 * * *'        # Jam 04:00 UTC
    - cron: '30 4 * * *'       # Jam 04:30 UTC
    - cron: '0 5 * * *'        # Jam 05:00 UTC
    - cron: '30 5 * * *'       # Jam 05:30 UTC
    - cron: '0 6 * * *'        # Jam 06:00 UTC
    - cron: '30 6 * * *'       # Jam 06:30 UTC
    - cron: '0 7 * * *'        # Jam 07:00 UTC
  workflow_dispatch:  # Manual trigger

jobs:
  auto-apply:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
      
      - name: Check daily limit
        id: check-limit
        run: |
          python -c "
          from scheduler import DailyScheduler
          scheduler = DailyScheduler()
          status = scheduler.can_apply()
          print(f'can_apply={status[\"can_apply\"]}')
          print(f'remaining={status[\"remaining_today\"]}')
          "
      
      - name: Run auto-apply
        if: steps.check-limit.outputs.can_apply == 'true'
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python main.py fill-db --limit ${{ steps.check-limit.outputs.remaining }}
      
      - name: Send Telegram notification
        if: always()
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python -c "
          import os
          import requests
          from scheduler import DailyScheduler
          
          scheduler = DailyScheduler()
          stats = scheduler.get_daily_stats()
          
          token = os.getenv('TELEGRAM_TOKEN')
          chat_id = os.getenv('TELEGRAM_CHAT_ID')
          
          if token and chat_id:
              msg = f'''
🤖 *Bot Auto-Apply Status*
📅 {stats['date']}

📊 Hari Ini: {stats['applied']}/{stats['max']}
✅ Total: {stats['total_all_time']}
📈 Success Rate: {stats['success_rate']:.1f}%
'''
              requests.post(f'https://api.telegram.org/bot{token}/sendMessage', 
                          json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'})
          "
"""
    return workflow


def create_railway_config():
    """Buat konfigurasi untuk Railway.app (gratis)"""
    config = """
# Railway.app Configuration
# Deploy gratis di railway.app

[build]
builder = "nixpacks"

[deploy]
startCommand = "python scheduler_runner.py"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

[env]
PYTHON_VERSION = "3.11"
GROQ_API_KEY = "${{GROQ_API_KEY}}"
TELEGRAM_TOKEN = "${{TELEGRAM_TOKEN}}"
TELEGRAM_CHAT_ID = "${{TELEGRAM_CHAT_ID}}"
"""
    return config


def create_render_config():
    """Buat konfigurasi untuk Render.com (gratis)"""
    config = """
# Render.com Configuration
# Deploy gratis di render.com

services:
  - type: worker
    name: job-auto-apply-bot
    env: python
    buildCommand: pip install -r requirements.txt && playwright install chromium
    startCommand: python scheduler_runner.py
    envVars:
      - key: GROQ_API_KEY
        sync: false
      - key: TELEGRAM_TOKEN
        sync: false
      - key: TELEGRAM_CHAT_ID
        sync: false
"""
    return config


def create_scheduler_runner():
    """Runner script untuk cloud execution"""
    runner = '''"""
SCHEDULER RUNNER - Jalankan di cloud (GitHub Actions / Railway / Render)
"""
import time
import asyncio
import os
from datetime import datetime
from scheduler import DailyScheduler
from core import SmartFormFiller
from config import get_config

async def run_once():
    """Jalankan satu iterasi"""
    scheduler = DailyScheduler()
    
    # Cek apakah boleh apply
    status = scheduler.can_apply()
    
    if not status["can_apply"]:
        print(f"[SKIP] {status['reason']}")
        return
    
    config = get_config()
    filler = SmartFormFiller(config)
    
    if not await filler.init_browser():
        print("[ERROR] Failed to init browser")
        return
    
    try:
        # TODO: Get jobs from database
        # For now, just log
        print(f"[RUN] Can apply {status['remaining_today']} more jobs today")
        
        # Record attempt
        scheduler.record_application("test", "test", False)
        
    finally:
        await filler.close_browser()

def main():
    """Main scheduler loop"""
    scheduler = DailyScheduler()
    
    print(scheduler.get_schedule_display())
    
    # Check status
    status = scheduler.can_apply()
    
    if status["can_apply"]:
        print("[START] Running auto-apply...")
        asyncio.run(run_once())
    else:
        print(f"[WAIT] {status['reason']}")
        if status.get("next_available_time"):
            print(f"[NEXT] Available at: {status['next_available_time']}")

if __name__ == "__main__":
    main()
'''
    return runner


if __name__ == "__main__":
    # Just show status
    scheduler = DailyScheduler()
    print(scheduler.get_schedule_display())
    
    status = scheduler.can_apply()
    print(f"Can apply now: {status['can_apply']}")
    print(f"Reason: {status['reason'] if status['reason'] else 'OK'}")
    print(f"Remaining today: {status['remaining_today']}")
