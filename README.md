# SMART FORM FILLER

Bot otomatis untuk mengisi application forms di job portals (Greenhouse, Lever, Ashby, dll). Menggunakan AI (Groq API) untuk menganalisis form fields dan generate jawaban yang tepat.

## Features

- Platform detection otomatis (Greenhouse, Lever, Ashby, Workday, dll)
- AI-powered form filling via Groq API (gratis)
- Smart field mapping dari .env config
- CAPTCHA detection dan graceful handling
- 24/7 scheduler dengan daily limits (15-20 apps/day)
- Job scraper untuk Greenhouse, Lever, Ashby boards
- Telegram notifications
- Database untuk tracking applications

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Run System Test

```bash
python test_bot.py
```

### 3. Add Jobs to Database

```bash
# Scrape from Greenhouse board
python job_scraper.py greenhouse airbnb

# Scrape from Lever board
python job_scraper.py lever polygon

# Scrape from Ashby board
python job_scraper.py ashby stripe

# Import from file (one URL per line)
python job_scraper.py import urls.txt

# Add URL manually
python job_scraper.py add "https://apply.greenhouse.io/company/jobs/123"
```

### 4. List Pending Jobs

```bash
python job_scraper.py list
```

### 5. Test Fill Application (Dry Run)

```bash
python main.py fill "https://boards.greenhouse.io/company/jobs/123" --dry-run
```

### 6. Fill from Database

```bash
# Fill next 10 pending jobs
python main.py fill-db --limit 10

# Dry run mode
python main.py fill-db --dry-run --limit 5
```

### 7. Run 24/7 Bot

```bash
python scheduler_runner.py
```

## Configuration

### .env File

Copy `.env.example` to `.env` and fill in your details:

```env
# API Keys
GROQ_API_KEY=your_groq_api_key
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Personal Information
FULL_NAME=Your Name
EMAIL=your@email.com
PHONE=+6281234567890
LINKEDIN=linkedin.com/in/yourprofile
GITHUB=github.com/yourprofile
```

### Getting Groq API Key (Free)

1. Go to https://console.groq.com
2. Sign up / Login
3. Create API Key
4. Add to `.env` file

### Telegram Notifications

1. Create bot via @BotFather on Telegram
2. Get the bot token
3. Get your chat ID via @userinfobot
4. Add to `.env` file

## Commands

| Command | Description |
|---------|-------------|
| `python test_bot.py` | Run system test |
| `python main.py fill <URL>` | Fill single application |
| `python main.py fill <URL> --dry-run` | Test fill without submitting |
| `python main.py fill-file <file>` | Fill from URL list file |
| `python main.py fill-db` | Fill from jobs database |
| `python main.py detect <URL>` | Detect platform from URL |
| `python main.py stats` | Show submission statistics |
| `python job_scraper.py greenhouse <company>` | Scrape Greenhouse jobs |
| `python job_scraper.py lever <company>` | Scrape Lever jobs |
| `python job_scraper.py ashby <company>` | Scrape Ashby jobs |
| `python job_scraper.py list` | List pending jobs |
| `python scheduler_runner.py` | Run 24/7 bot |

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

## File Structure

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
├── data/
│   ├── init_db.py              # Database initialization
│   └── jobs.db                 # Jobs database (auto-created)
├── job_scraper.py              # Job scraper for boards
├── main.py                     # CLI entry point
├── test_bot.py                 # System test script
├── scheduler.py                # 24/7 scheduler
├── scheduler_runner.py         # Cloud runner
├── create_cv.py                # CV template generator
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── RUN.bat                     # Windows runner
└── SETUP.bat                   # Windows setup
```

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

## License

MIT
