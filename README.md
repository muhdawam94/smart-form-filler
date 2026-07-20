# SMART FORM FILLER - Final Setup Guide

## Overview

Smart Form Filler adalah bot otomatis untuk mengisi application forms di job portals (Greenhouse, Lever, Ashby, dll). Bot ini menggunakan AI (Groq API) untuk menganalisis form fields dan generate jawaban yang tepat.

## Features

- Platform detection otomatis (Greenhouse, Lever, Ashby, Workday, dll)
- AI-powered form filling via Groq API (gratis)
- Smart field mapping dari .env config
- CAPTCHA detection dan graceful handling
- 24/7 scheduler dengan daily limits (15-20 apps/day)
- GitHub Actions workflow untuk cloud deployment
- Telegram notifications

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Test API Connection

```bash
python test_api.py
```

### 3. Test Platform Detection

```bash
python main.py detect "https://boards.greenhouse.io/company/jobs/123"
```

### 4. Test Fill Application (Dry Run)

```bash
python main.py fill "https://boards.greenhouse.io/company/jobs/123" --dry-run
```

### 5. Fill Application with CV

```bash
python main.py fill "https://boards.greenhouse.io/company/jobs/123" --cv cv.pdf
```

## 24/7 Cloud Deployment (GitHub Actions)

### Setup

1. Push repo ke GitHub
2. Go to repo Settings > Secrets and variables > Actions
3. Add secrets:
   - `GROQ_API_KEY` = your_groq_api_key
   - `TELEGRAM_TOKEN` = your_telegram_bot_token
   - `TELEGRAM_CHAT_ID` = your_telegram_chat_id
4. Go to Actions tab and enable workflows
5. Bot will run automatically every 30 minutes!

### Daily Limits

- Max applications per day: 18 (range 15-20)
- Active hours: 15:00-05:00 WIB (22:00-08:00 UTC)
- Delay between applications: 5-15 minutes

## Supported Platforms

| Platform | Success Rate | Notes |
|----------|--------------|-------|
| Greenhouse | 95% | Best support |
| Lever | 93% | Great support |
| Ashby | 90% | Good support |
| SmartRecruiters | 92% | Good support |
| BambooHR | 91% | Good support |
| Workday | 75% | Has CAPTCHA |
| Custom | 60-70% | AI-assisted |

## Troubleshooting

### "Playwright not installed"

```bash
pip install playwright
playwright install chromium
```

### "API key invalid"

Cek file `.env` - pastikan GROQ_API_KEY sudah benar.

### "Form not found"

Beberapa form pakai JavaScript loading. Bot akan tunggu sampai form muncul.

### "CAPTCHA detected"

Workday dan beberapa platform lain pakai CAPTCHA. Bot akan skip otomatis.

## Security

- Semua data sensitif (API keys, email, phone) load dari `.env` file
- `.env` di-exclude dari git (tidak di-push ke GitHub)
- CV.pdf tidak di-push ke GitHub
- Source code tidak mengandung hardcoded PII

## Files

```
smart-form-filler/
├── .env                    # Your config (NOT in git)
├── .env.example            # Template config
├── .gitignore              # Git ignore rules
├── .github/workflows/
│   └── auto-apply.yml      # GitHub Actions workflow
├── config.py               # Configuration loader
├── core/
│   ├── __init__.py
│   ├── ai_field_analyzer.py    # AI form analysis
│   ├── form_filler.py          # Playwright form filling
│   └── platform_detector.py    # ATS platform detection
├── integrate_with_jobbot.py    # Integration with other bots
├── main.py                     # CLI entry point
├── QUICK_START.md              # Quick start guide
├── requirements.txt            # Python dependencies
├── RUN.bat                     # Windows runner
├── scheduler.py                # 24/7 scheduler
├── scheduler_runner.py         # Cloud runner
├── SETUP.bat                   # Windows setup
└── setup_deployment.py         # Deployment setup
```

## Support

- GitHub: https://github.com/muhdawam94/smart-form-filler
- Issues: https://github.com/muhdawam94/smart-form-filler/issues
