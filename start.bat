@echo off
title RecoverAI Launcher
color 0A
echo.
echo  ========================================
echo    RecoverAI - Launching System
echo  ========================================
echo.

:: ─── Check Python ───
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

:: ─── Install backend deps (silently if already installed) ───
echo [1/3] Checking backend dependencies...
pip install -r backend\requirements.txt -q --disable-pip-version-check
echo       Done.

:: ─── Start FastAPI backend in a new window ───
echo [2/3] Starting RecoverAI backend (port 8000)...
start "RecoverAI Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

:: ─── Open frontend in default browser ───
echo [3/3] Opening dashboard in browser...
start "" "%~dp0frontend\index.html"

echo.
echo  ✅ RecoverAI is running!
echo     Backend API  : http://localhost:8000
echo     API Docs     : http://localhost:8000/docs
echo     Frontend     : frontend/index.html (opened in browser)
echo.
echo  Press any key to exit this launcher (backend keeps running)
echo.
pause
