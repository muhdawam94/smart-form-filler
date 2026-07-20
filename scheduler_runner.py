"""
SCHEDULER RUNNER - Jalankan di cloud
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
        print(f"[RUN] Can apply {status['remaining_today']} more jobs today")
        scheduler.record_application("test", "test", False)
        
    finally:
        await filler.close_browser()

def main():
    """Main scheduler loop"""
    scheduler = DailyScheduler()
    
    print(scheduler.get_schedule_display())
    
    status = scheduler.can_apply()
    
    if status["can_apply"]:
        print("[START] Running auto-apply...")
        asyncio.run(run_once())
    else:
        print(f"[WAIT] {status['reason']}")

if __name__ == "__main__":
    main()
