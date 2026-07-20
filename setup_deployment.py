"""
SETUP SCRIPT - Generate deployment files untuk 24/7 bot
Jalankan sekali untuk setup
"""
import os

def create_github_actions_workflow():
    """Buat GitHub Actions workflow"""
    workflow = """name: 24/7 Job Auto-Apply Bot

on:
  schedule:
    # Run setiap 30 menit dari jam 15:00-05:00 WIB (08:00-22:00 UTC)
    - cron: '0,30 8-21 * * *'
    - cron: '0 22 * * *'
    - cron: '30 22 * * *'
    - cron: '0 23 * * *'
    - cron: '30 23 * * *'
    - cron: '0 0 * * *'
    - cron: '30 0 * * *'
    - cron: '0 1 * * *'
    - cron: '30 1 * * *'
    - cron: '0 2 * * *'
    - cron: '30 2 * * *'
    - cron: '0 3 * * *'
    - cron: '30 3 * * *'
    - cron: '0 4 * * *'
    - cron: '30 4 * * *'
    - cron: '0 5 * * *'
    - cron: '30 5 * * *'
    - cron: '0 6 * * *'
    - cron: '30 6 * * *'
    - cron: '0 7 * * *'
  workflow_dispatch:

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
"""
    return workflow


def create_requirements():
    """Buat requirements.txt"""
    return """playwright>=1.40.0
groq>=0.4.0
openai>=1.0.0
fake-useragent>=1.4.0
python-dotenv>=1.0.0
requests>=2.31.0
"""


def main():
    """Generate all deployment files"""
    print("Generating deployment files...")
    
    # GitHub Actions
    os.makedirs(".github/workflows", exist_ok=True)
    with open(".github/workflows/auto-apply.yml", "w") as f:
        f.write(create_github_actions_workflow())
    print("Created: .github/workflows/auto-apply.yml")
    
    # Requirements
    with open("requirements.txt", "w") as f:
        f.write(create_requirements())
    print("Created: requirements.txt")
    
    # Create .gitignore
    gitignore = """__pycache__/
*.pyc
.env
*.db
data/
scheduler_state.json
"""
    with open(".gitignore", "w") as f:
        f.write(gitignore)
    print("Created: .gitignore")
    
    print("\nDone! Next steps:")
    print("1. Push to GitHub")
    print("2. Go to repo Settings > Secrets and variables > Actions")
    print("3. Add secrets: GROQ_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID")
    print("4. Go to Actions tab and enable workflows")
    print("5. Bot will run automatically every 30 minutes!")


if __name__ == "__main__":
    main()
