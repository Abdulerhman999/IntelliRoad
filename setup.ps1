# ============================================================
# Road Cost Predictor - Ultimate Clean Setup
# ============================================================
# 1. Uninstalls wrong Python & Node.js versions.
# 2. Installs correct Python 3.11 & Node.js LTS.
# 3. Creates correct database (ml_db).
# 4. Installs all libraries.

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ROAD COST PREDICTOR - FULL SYSTEM REPAIR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PROJECT_DIR

# ------------------------------------------------------------
# HELPER: REFRESH ENVIRONMENT
# ------------------------------------------------------------
function Refresh-Env {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

# ------------------------------------------------------------
# STEP 1: CHECK & FIX PYTHON
# ------------------------------------------------------------
Write-Host "[STEP 1/6] Validating Python..." -ForegroundColor Cyan

$installPython = $false
try {
    $pyVer = python --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $pyVer -match "Python 3.11") {
        Write-Host "[OK] Found $pyVer" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Found incompatible/broken Python: $pyVer" -ForegroundColor Yellow
        Write-Host "Uninstalling old Python versions..." -ForegroundColor DarkGray
        try {
            # Try to uninstall common versions
            winget uninstall --id Python.Python.3.12 -e --accept-source-agreements 2>$null
            winget uninstall --id Python.Python.3.10 -e --accept-source-agreements 2>$null
            winget uninstall --id Python.Python.3.9 -e --accept-source-agreements 2>$null
        } catch { Write-Host "  (Uninstall attempt finished)" -ForegroundColor DarkGray }
        $installPython = $true
    }
} catch {
    Write-Host "[INFO] Python not found." -ForegroundColor DarkGray
    $installPython = $true
}

if ($installPython) {
    Write-Host "Installing Python 3.11..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.11 --scope machine --accept-package-agreements --accept-source-agreements
    Refresh-Env
}
Write-Host ""

# ------------------------------------------------------------
# STEP 2: CHECK & FIX NODE.JS
# ------------------------------------------------------------
Write-Host "[STEP 2/6] Validating Node.js..." -ForegroundColor Cyan

$installNode = $false
try {
    $nodeVer = node --version 2>&1
    # Check if version is v20 or v22 (Current LTS versions)
    if ($LASTEXITCODE -eq 0 -and ($nodeVer -match "v20" -or $nodeVer -match "v22")) {
        Write-Host "[OK] Found modern Node.js: $nodeVer" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Found old/incompatible Node.js: $nodeVer" -ForegroundColor Yellow
        Write-Host "Uninstalling old Node.js..." -ForegroundColor DarkGray
        try {
            winget uninstall --id OpenJS.NodeJS -e --accept-source-agreements 2>$null
            winget uninstall --id OpenJS.NodeJS.LTS -e --accept-source-agreements 2>$null
        } catch { Write-Host "  (Uninstall attempt finished)" -ForegroundColor DarkGray }
        $installNode = $true
    }
} catch {
    Write-Host "[INFO] Node.js not found." -ForegroundColor DarkGray
    $installNode = $true
}

if ($installNode) {
    Write-Host "Installing Node.js LTS..." -ForegroundColor Yellow
    winget install -e --id OpenJS.NodeJS.LTS --scope machine --accept-package-agreements --accept-source-agreements
    Refresh-Env
    
    # Verify installation
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-Host "------------------------------------------------------------" -ForegroundColor Red
        Write-Host "[ATTENTION] Node.js installed, but requires a restart." -ForegroundColor Yellow
        Write-Host "Please CLOSE this window, OPEN a new one, and run setup.ps1 again." -ForegroundColor White
        Write-Host "------------------------------------------------------------" -ForegroundColor Red
        exit
    }
}
Write-Host ""

# ------------------------------------------------------------
# STEP 3: RESET VIRTUAL ENVIRONMENT
# ------------------------------------------------------------
Write-Host "[STEP 3/6] Resetting Python Environment..." -ForegroundColor Cyan

if (Test-Path "venv") {
    Write-Host "Removing old venv..." -ForegroundColor DarkGray
    Remove-Item "venv" -Recurse -Force
}

Write-Host "Creating fresh venv..."
python -m venv venv
$VENV_PYTHON = "$PROJECT_DIR\venv\Scripts\python.exe"
$VENV_PIP    = "$PROJECT_DIR\venv\Scripts\pip.exe"

if (-not (Test-Path $VENV_PYTHON)) {
    Write-Host "[ERROR] Failed to create venv. Check Python installation." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Environment ready." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------
# STEP 4: DATABASE SETUP (ml_db)
# ------------------------------------------------------------
Write-Host "[STEP 4/6] Configuring Database (ml_db)..." -ForegroundColor Cyan

if (-not (Test-Path "sql")) { New-Item -ItemType Directory "sql" | Out-Null }
$schemaPath = "$PROJECT_DIR\sql\schema.sql"

# Schema definition for ml_db
$schemaContent = @"
CREATE DATABASE IF NOT EXISTS ml_db;
USE ml_db;

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    role ENUM('admin', 'employee') DEFAULT 'employee',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT
);

CREATE TABLE IF NOT EXISTS material_categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100),
    display_order INT DEFAULT 0
);
INSERT IGNORE INTO material_categories (category_name, display_order) VALUES 
('Civil Works', 1), ('Asphalt', 2), ('Steel', 3), ('Aggregates', 4);
"@
Set-Content -Path $schemaPath -Value $schemaContent

Write-Host "Please enter your MySQL ROOT password:" -ForegroundColor Yellow
try {
    # Create DB and Apply Schema
    mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS ml_db;"
    Get-Content $schemaPath | mysql -u root -p ml_db
    Write-Host "[SUCCESS] Database 'ml_db' ready." -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Database setup failed. Check password." -ForegroundColor Red
    throw $_
}
Write-Host ""

# ------------------------------------------------------------
# STEP 5: BACKEND DEPENDENCIES
# ------------------------------------------------------------
Write-Host "[STEP 5/6] Installing Backend Libraries..." -ForegroundColor Cyan

& $VENV_PYTHON -m pip install --upgrade pip | Out-Null
$pkgs = @("fastapi", "uvicorn[standard]", "pymysql", "pyyaml", "python-multipart")
foreach ($pkg in $pkgs) {
    Write-Host "Installing $pkg..." -ForegroundColor Yellow
    & $VENV_PIP install $pkg | Out-Null
}

if (Test-Path "requirements.txt") {
    Write-Host "Installing requirements.txt..."
    & $VENV_PIP install -r requirements.txt | Out-Null
}
Write-Host "[OK] Backend ready." -ForegroundColor Green
Write-Host ""

# ------------------------------------------------------------
# STEP 6: FRONTEND DEPENDENCIES
# ------------------------------------------------------------
Write-Host "[STEP 6/6] checking Frontend..." -ForegroundColor Cyan

if (Test-Path "road-cost-frontend") {
    Set-Location "$PROJECT_DIR\road-cost-frontend"
    Write-Host "Running npm install..."
    cmd /c "npm install"
    Set-Location $PROJECT_DIR
    Write-Host "[OK] Frontend ready." -ForegroundColor Green
} else {
    Write-Host "[WARN] Frontend folder not found." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SYSTEM REPAIRED & READY" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "1. Backend: .\venv\Scripts\python.exe app.py" -ForegroundColor White
Write-Host "2. Frontend: cd road-cost-frontend; npm start" -ForegroundColor White
Write-Host ""
Read-Host "Press ENTER to exit"