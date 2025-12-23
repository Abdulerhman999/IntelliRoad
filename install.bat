@echo off
:: ============================================================
:: Road Cost Predictor - One-Click Installer
:: ============================================================
TITLE Road Cost Predictor Setup

echo.
echo ============================================================
echo  LAUNCHING SETUP SCRIPT...
echo ============================================================
echo.
echo This window will close automatically when the setup starts.
echo.

:: This command launches PowerShell, bypasses security checks, and runs your script
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0setup.ps1'"

:: Pause only if there was a critical error launching PowerShell itself
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Could not launch PowerShell.
    pause
)