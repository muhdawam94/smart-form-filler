@echo off
title Smart Form Filler - Setup
echo ========================================
echo SMART FORM FILLER - Setup
echo ========================================
echo.

echo [1/4] Installing Python dependencies...
pip install -r requirements.txt

echo.
echo [2/4] Installing Playwright...
playwright install chromium

echo.
echo [3/4] Running integration setup...
python integrate_with_jobbot.py

echo.
echo [4/4] Setup complete!
echo.
echo ========================================
echo NEXT STEPS:
echo 1. Set GROQ_API_KEY (optional, for AI features)
echo 2. python main.py fill "URL" --dry-run
echo ========================================
pause
