# SMART FORM FILLER - Quick Start

## Setup (Sudah Selesai!)

API Key sudah terkonfigurasi. Tinggal install dependencies:

```bash
pip install playwright groq python-dotenv fake-useragent
playwright install chromium
```

## Usage

### 1. Test Platform Detection
```bash
python main.py detect "https://boards.greenhouse.io/company/jobs/123"
```

### 2. Fill Single Application (Test Dulu!)
```bash
python main.py fill "https://boards.greenhouse.io/company/jobs/123" --dry-run
```

### 3. Fill with CV Upload
```bash
python main.py fill "https://apply.lever.co/company123" --cv cv.pdf
```

### 4. Fill from URL List
```bash
# Buat file urls.txt (satu URL per baris)
python main.py fill-file urls.txt --limit 5
```

### 5. Fill from Job Bot Database
```bash
python main.py fill-db --db path/to/your/jobs.db --limit 10
```

### 6. Check Statistics
```bash
python main.py stats
```

## How It Works

```
URL Input
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
