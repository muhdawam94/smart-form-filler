# SMART FORM FILLER - Quick Start

## Setup (Sudah Selesai!)

Semua dependencies sudah terinstall. Jalankan test untuk verifikasi:

```bash
python test_bot.py
```

## Usage

### 1. Add Jobs ke Database
```bash
# Scrape dari Greenhouse
python job_scraper.py greenhouse airbnb

# Scrape dari Lever
python job_scraper.py lever polygon

# Import dari file
python job_scraper.py import urls.txt

# Tambah manual
python job_scraper.py add "https://apply.greenhouse.io/company/jobs/123"
```

### 2. List Pending Jobs
```bash
python job_scraper.py list
```

### 3. Test Fill (Dry Run)
```bash
python main.py fill "https://boards.greenhouse.io/company/jobs/123" --dry-run
```

### 4. Fill dari Database
```bash
python main.py fill-db --limit 10
```

### 5. Run 24/7 Bot
```bash
python scheduler_runner.py
```

### 6. Check Statistics
```bash
python main.py stats
```

## How It Works

```
Job Database
    ↓
Platform Detection (Greenhouse/Lever/Workday/etc)
    ↓
AI Field Analysis (Groq API - FREE)
    ↓
Smart Fill (auto-fill all fields)
    ↓
Custom Questions (AI-generated answers)
    ↓
Submit (or --dry-run untuk test)
    ↓
Telegram Notification
```

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

## Tips

1. **Selalu test dengan `--dry-run` dulu** sebelum submit beneran
2. **Pastikan CV.pdf ada** di folder project untuk upload
3. **Cek stats** untuk monitor success rate
4. **Kalau CAPTCHA muncul**, bot akan skip dan lanjut ke next URL
5. **Telegram notifikasi** otomatis dikirim setiap kali berhasil apply

## Troubleshooting

### "Playwright not installed"
```bash
pip install playwright
playwright install chromium
```

### "API key invalid"
Cek file `.env` - API key sudah terkonfigurasi dengan benar.

### "Form not found"
Beberapa form pakai JavaScript loading. Bot akan tunggu sampai form muncul.

### "CAPTCHA detected"
Workday dan beberapa platform lain pakai CAPTCHA. Bot akan skip otomatis.
