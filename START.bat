@echo off
REM ============================================================
REM Road Cost Predictor - Startup Script
REM ============================================================

color 0A
title Road Cost Predictor - Starting...

echo.
echo ============================================================
echo    ROAD COST PREDICTOR - STARTUP
echo ============================================================
echo.

REM Get the directory where the script is located
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo [1/6] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    echo.
    pause
    exit /b 1
)
python --version
echo [OK] Python found

echo.
echo [2/6] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js and try again
    echo.
    pause
    exit /b 1
)
node --version
echo [OK] Node.js found

echo.
echo [3/6] Checking MySQL...
mysql --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] MySQL CLI not found in PATH
    echo Please make sure MySQL server is running
    timeout /t 3 >nul
) else (
    mysql --version
    echo [OK] MySQL found
)

echo.
echo [4/6] Checking virtual environment...
if exist "venv\Scripts\activate.bat" (
    echo [OK] Virtual environment found
) else (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first
    echo.
    pause
    exit /b 1
)

echo.
echo [5/6] Checking model files...
if exist "models\xgb_model.joblib" (
    if exist "models\scaler.joblib" (
        echo [OK] ML model files found
    ) else (
        echo [WARNING] Scaler file missing - predictions may fail
        timeout /t 2 >nul
    )
) else (
    echo [WARNING] ML model not found - will use fallback calculations
    echo You can train the model later with: python -m backend.ml.train_model
    timeout /t 3 >nul
)

echo.
echo [6/6] Starting servers...
echo.
echo ============================================================
echo    STARTING BACKEND SERVER (Port 8000)
echo ============================================================
echo.

REM Activate virtual environment and start backend in new window
start "Road Cost Predictor - Backend" cmd /k "cd /d "%PROJECT_DIR%" && call venv\Scripts\activate.bat && echo. && echo ============================================== && echo    BACKEND SERVER STARTING... && echo ============================================== && echo. && python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 8 /nobreak >nul

echo.
echo ============================================================
echo    STARTING FRONTEND SERVER (Port 3000)
echo ============================================================
echo.

REM Check if node_modules exists before starting
if not exist "%PROJECT_DIR%road-cost-frontend\node_modules" (
    echo [ERROR] Frontend dependencies not installed!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Start frontend in new window with explicit path
start "Road Cost Predictor - Frontend" cmd /k "cd /d "%PROJECT_DIR%road-cost-frontend" && echo. && echo ============================================== && echo    FRONTEND SERVER STARTING... && echo ============================================== && echo. && npm start"

REM Wait for frontend to start
echo Waiting for frontend to initialize...
timeout /t 10 /nobreak >nul

echo.
echo ============================================================
echo    OPENING BROWSER...
echo ============================================================
echo.

REM Open browser
start http://localhost:3000

echo.
echo ============================================================
echo    APPLICATION STARTED SUCCESSFULLY!
echo ============================================================
echo.
echo Frontend:  http://localhost:3000
echo Backend:   http://localhost:8000
echo API Docs:  http://localhost:8000/docs
echo.
echo Two new terminal windows have opened:
echo   1. Backend Server  (Green title bar)
echo   2. Frontend Server (Green title bar)
echo.
echo IMPORTANT: Keep both terminal windows open!
echo.
echo ============================================================
echo    HOW TO USE
echo ============================================================
echo.
echo 1. Browser should open automatically
echo 2. If not, open: http://localhost:3000
echo 3. Click "Create Account" to register
echo 4. Login and start creating projects!
echo.
echo ============================================================
echo    HOW TO STOP
echo ============================================================
echo.
echo Option 1: Close both terminal windows
echo Option 2: Double-click STOP.bat
echo Option 3: Press CTRL+C in each terminal window
echo.
echo ============================================================
echo.
echo You can close this window now.
echo The application will keep running in the other windows.
echo.
pause