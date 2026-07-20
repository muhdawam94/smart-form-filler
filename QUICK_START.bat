@echo off
title Smart Form Filler - Quick Start
echo ========================================
echo SMART FORM FILLER - Quick Start
echo ========================================
echo.
echo [1] Test API Connection
echo [2] Test Platform Detection
echo [3] Test Fill Application (Dry Run)
echo [4] Fill Application with CV
echo [5] Check Statistics
echo [6] Run Scheduler
echo [7] Open GitHub Repo
echo [8] Exit
echo.
set /p choice="Pilih (1-8): "

if "%choice%"=="1" (
    echo.
    echo Testing API Connection...
    python test_api.py
) else if "%choice%"=="2" (
    echo.
    set /p url="Masukkan URL: "
    python main.py detect "%url%"
) else if "%choice%"=="3" (
    echo.
    set /p url="Masukkan URL: "
    python main.py fill "%url%" --dry-run
) else if "%choice%"=="4" (
    echo.
    set /p url="Masukkan URL: "
    python main.py fill "%url%" --cv cv.pdf
) else if "%choice%"=="5" (
    echo.
    python main.py stats
) else if "%choice%"=="6" (
    echo.
    python scheduler.py
) else if "%choice%"=="7" (
    start https://github.com/muhdawam94/smart-form-filler
) else if "%choice%"=="8" (
    exit
)

echo.
pause
