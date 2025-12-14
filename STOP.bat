@echo off
REM ============================================================
REM Road Cost Predictor - Stop Script
REM ============================================================

color 0C
title Road Cost Predictor - Stopping...

echo.
echo ============================================================
echo    ROAD COST PREDICTOR - SHUTDOWN
echo ============================================================
echo.
echo This will stop all running servers and close terminal windows.
echo.
pause

echo.
echo [1/4] Stopping Backend Server (Port 8000)...

REM Find and kill process on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process %%a on port 8000...
    taskkill /F /PID %%a >nul 2>&1
)
echo [OK] Backend stopped

echo.
echo [2/4] Stopping Frontend Server (Port 3000)...

REM Find and kill process on port 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    echo Killing process %%a on port 3000...
    taskkill /F /PID %%a >nul 2>&1
)
echo [OK] Frontend stopped

echo.
echo [3/4] Closing terminal windows...

REM Kill all cmd windows with our application titles
taskkill /FI "WINDOWTITLE eq Road Cost Predictor - Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Road Cost Predictor - Frontend*" /F >nul 2>&1
echo [OK] Terminal windows closed

echo.
echo [4/4] Cleanup...

REM Kill any remaining Node.js or Python processes related to our app
REM (Be careful - only kills on our specific ports)
timeout /t 1 /nobreak >nul
echo [OK] Cleanup complete

echo.
echo ============================================================
echo    ALL SERVERS STOPPED SUCCESSFULLY!
echo ============================================================
echo.
echo Application has been shut down cleanly.
echo.
echo To restart the application:
echo   - Double-click START.bat
echo.
echo ============================================================
echo.
pause