@echo off
REM ============================================================
REM Road Cost Predictor - Startup Script (START.bat)
REM ============================================================

color 0A
title Road Cost Predictor - Starting...

echo.
echo ============================================================
echo     ROAD COST PREDICTOR - STARTUP
echo ============================================================
echo.

REM Get the directory where the script is located
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please run INSTALL.bat first.
    pause
    exit /b 1
)

echo [2/6] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    pause
    exit /b 1
)

echo [3/6] Checking MySQL...
mysql --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] MySQL CLI not found. Ensure MySQL is running.
)

echo [4/6] Checking virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found! Please run INSTALL.bat.
    pause
    exit /b 1
)

echo [5/6] Checking model files...
if not exist "models\xgb_model.joblib" (
    echo [WARNING] ML model not found - using fallback calculations.
)

echo.
echo [6/6] Starting servers...
echo.
echo ============================================================
echo     STARTING BACKEND SERVER (Port 8000)
echo ============================================================

REM Start backend in new window
start "Road Cost Predictor - Backend" cmd /k "cd /d "%PROJECT_DIR%" && call venv\Scripts\activate.bat && python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

echo.
echo ============================================================
echo     STARTING FRONTEND SERVER (Port 3000)
echo ============================================================

if not exist "%PROJECT_DIR%road-cost-frontend\node_modules" (
    echo [ERROR] Frontend dependencies not installed! Run INSTALL.bat.
    pause
    exit /b 1
)

REM START FRONTEND: set BROWSER=none stops React from opening a tab automatically
start "Road Cost Predictor - Frontend" cmd /k "cd /d "%PROJECT_DIR%road-cost-frontend" && set BROWSER=none && npm start"

echo.
echo Waiting for servers to initialize...
echo The website will open automatically in 10 seconds.
echo.
timeout /t 10 /nobreak >nul

REM --- THE FIX ---
REM This is the ONLY command that will open a browser tab.
start http://localhost:3000

echo.
echo ============================================================
echo     APPLICATION STARTED SUCCESSFULLY!
echo ============================================================
echo.
echo Frontend:  http://localhost:3000
echo Backend:   http://localhost:8000
echo.
echo IMPORTANT: Keep the two server windows open!
echo.
pause