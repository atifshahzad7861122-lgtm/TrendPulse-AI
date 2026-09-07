@echo off
setlocal enabledelayedexpansion

title TrendPulse AI - FastAPI Backend (Terminal 1)

echo ===============================================================================
echo                TRENDPULSE AI - DARAZ OPEN PLATFORM BACKEND
echo ===============================================================================
echo.
echo [1/3] Checking Python Environment...

rem Check for virtual environments
if exist ".venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment (venv)...
    call venv\Scripts\activate.bat
) else (
    echo [!] No local virtual environment found. Using system Python.
)

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] ERROR: Python is not installed or not found on PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

echo [2/3] Verifying Backend Dependencies...
python -c "import fastapi, uvicorn, pydantic" >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] ERROR: Required Python packages (fastapi, uvicorn, pydantic) not installed.
    echo Please run: pip install -r backend/requirements.txt
    pause
    exit /b 1
)

echo [3/3] Starting FastAPI Server on 127.0.0.1:8000...
echo.
echo ===============================================================================
echo  Local Backend URL : http://127.0.0.1:8000
echo  Swagger API Docs  : http://127.0.0.1:8000/docs
echo  Daraz Callback    : http://127.0.0.1:8000/api/v1/platforms/daraz/callback
echo ===============================================================================
echo.
echo [NOTE] To expose this backend to the Daraz Open Platform via HTTPS:
echo        Open TERMINAL 2 and run:
echo        cloudflared tunnel --url http://localhost:8000
echo.
echo Starting uvicorn server...
echo.

uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

if %errorlevel% neq 0 (
    echo.
    echo [X] Backend process exited with error code %errorlevel%.
    pause
)
