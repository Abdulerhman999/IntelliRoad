<# :
@echo off
TITLE IntelliRoad Installer
color 0B
cd /d "%~dp0"

echo ============================================================
echo   INTELLIROAD - ONE CLICK INSTALLER
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass ^
  -Command "iex ((Get-Content '%~f0') -join [Environment]::NewLine); Main-Setup"

echo.
echo ============================================================
echo   INSTALLATION COMPLETE
echo   Run START.bat to launch the project
echo ============================================================
pause
goto :eof
#>

# =================== POWERSHELL ===================

function Log($msg) {
    $msg | Tee-Object -FilePath "install.log" -Append
}

function Main-Setup {
    $ErrorActionPreference = "Stop"
    $PROJECT_DIR = Get-Location
    Log "`n=== INSTALL STARTED $(Get-Date) ==="

    # ------------------------------------------------
    # 1. ENVIRONMENT CHECK
    # ------------------------------------------------
    Log "[1/6] Checking Environment"

    try {
        $pyVer = python --version 2>&1
        if ($pyVer -match "3\.(11|12)") {
            Log " [OK] $pyVer"
        } else { throw }
    } catch {
        Log " [FIX] Installing Python 3.11"
        winget install -e --id Python.Python.3.11 --scope machine --accept-source-agreements
    }

    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Log " [FIX] Installing Node.js"
        winget install -e --id OpenJS.NodeJS.LTS --scope machine --accept-source-agreements
    } else {
        Log " [OK] Node.js found"
    }

    # ------------------------------------------------
    # 2. MYSQL DETECTION
    # ------------------------------------------------
    Log "[2/6] Detecting MySQL"

    $mysqlCmd = (Get-Command mysql -ErrorAction SilentlyContinue)?.Source
    if (-not $mysqlCmd) {
        $paths = @(
            "C:\xampp\mysql\bin\mysql.exe",
            "$env:ProgramFiles\MySQL\MySQL Server*\bin\mysql.exe"
        )
        foreach ($p in $paths) {
            $found = Get-ChildItem $p -ErrorAction SilentlyContinue | Select -First 1
            if ($found) { $mysqlCmd = $found.FullName; break }
        }
    }

    if (-not $mysqlCmd) {
        Log " [ERROR] MySQL not found"
        exit
    }

    # ------------------------------------------------
    # 3. DATABASE + USER SETUP (SECURE)
    # ------------------------------------------------
    Log "[3/6] Database Setup"

    Write-Host "Enter MySQL ROOT password (used only once):" -ForegroundColor Yellow
    $rootPass = Read-Host -AsSecureString
    $rootPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($rootPass)
    )

    $DB_NAME = "ml_db"
    $DB_USER = "intelliroad"
    $DB_PASS = -join ((33..126) | Get-Random -Count 16 | % {[char]$_})

    $env:MYSQL_PWD = $rootPassPlain

    try {
        & $mysqlCmd -u root -e "
        CREATE DATABASE IF NOT EXISTS $DB_NAME;
        CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
        GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
        FLUSH PRIVILEGES;
        " 2>$null
        Log " [OK] Database and user created"
    } catch {
        Log " [ERROR] Database setup failed"
        exit
    }

    # ------------------------------------------------
    # 4. SCHEMA IMPORT
    # ------------------------------------------------
    Log "[4/6] Importing Database Schema"

    if (-not (Test-Path "sql\schema.sql")) {
        Log " [ERROR] sql/schema.sql not found"
        exit
    }

    $env:MYSQL_PWD = $DB_PASS
    & $mysqlCmd -u $DB_USER $DB_NAME < "sql\schema.sql" 2>$null
    $env:MYSQL_PWD = $null

    Log " [OK] Schema imported"

    # ------------------------------------------------
    # 5. CONFIG.YAML UPDATE
    # ------------------------------------------------
    Log "[5/6] Updating config.yaml"

    if (Test-Path "config.yaml") {
        $cfg = Get-Content "config.yaml" -Raw
        $cfg = $cfg -replace 'user:\s*".*"', "user: ""$DB_USER"""
        $cfg = $cfg -replace 'password:\s*".*"', "password: ""$DB_PASS"""
        $cfg = $cfg -replace 'db:\s*".*"', "db: ""$DB_NAME"""
        Set-Content "config.yaml" $cfg
        Log " [OK] config.yaml updated"
    } else {
        Log " [WARN] config.yaml not found"
    }

    # ------------------------------------------------
    # 6. BACKEND SETUP
    # ------------------------------------------------
    Log "[6/6] Backend Setup"

    if (Test-Path "venv") { Remove-Item venv -Recurse -Force }
    python -m venv venv --upgrade-deps

    & ".\venv\Scripts\pip.exe" install fastapi "uvicorn[standard]" pymysql pyyaml python-multipart | Out-Null
    if (Test-Path "requirements.txt") {
        & ".\venv\Scripts\pip.exe" install -r requirements.txt | Out-Null
    }

    # ------------------------------------------------
    # 7. FRONTEND SETUP
    # ------------------------------------------------
    Log "[7/7] Frontend Setup"

    if (Test-Path "road-cost-frontend") {
        Set-Location "road-cost-frontend"
        cmd /c "npm install" | Out-Null
        Set-Location $PROJECT_DIR
        Log " [OK] Frontend installed"
    }

    Log "=== INSTALL COMPLETED SUCCESSFULLY ==="
}
