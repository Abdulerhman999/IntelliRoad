<# :
@echo off
TITLE IntelliRoad Installer
color 0B
cd /d "%~dp0"

echo ============================================================
echo   INTELLIROAD - ONE CLICK INSTALLER
echo ============================================================
echo.

REM Launch PowerShell and execute MainSetup function
powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((Get-Content '%~f0') -join [Environment]::NewLine); MainSetup"

echo.
echo ============================================================
echo   INSTALLATION COMPLETE
echo   Run START.bat to launch the project
echo ============================================================
pause
goto :eof
#>

# ========================= POWERSHELL =========================
function Log($msg) {
    Write-Host $msg
    $msg | Out-File -FilePath "install.log" -Append
}

function MainSetup {

    $ErrorActionPreference = "Stop"
    $PROJECT_DIR = Get-Location
    Log "`n=== INSTALL STARTED $(Get-Date) ==="

    # ------------------------------------------------
    # 1. ENVIRONMENT CHECK (Python + Node)
    # ------------------------------------------------
    Log "[1/6] Checking Environment"

    if (Get-Command python -ErrorAction SilentlyContinue) {
        $PYTHON = "python"
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $PYTHON = "py"
    } else {
        Log "[ERROR] Python not found. Install Python 3.10+ and enable 'Add to PATH'"
        exit
    }
    Log "[OK] Python detected: $PYTHON"

    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Log "[FIX] Installing Node.js..."
        winget install -e --id OpenJS.NodeJS.LTS --scope machine --accept-source-agreements
    } else {
        Log "[OK] Node.js found"
    }

    # ------------------------------------------------
    # 2. MYSQL DETECTION
    # ------------------------------------------------
    Log "[2/6] Detecting MySQL"

    $mysqlPaths = @(
        "C:\xampp\mysql\bin\mysql.exe",
        "$env:ProgramFiles\MySQL\MySQL Server*\bin\mysql.exe",
        "$env:ProgramFiles(x86)\MySQL\MySQL Server*\bin\mysql.exe"
    )

    $mysqlCmd = $null
    foreach ($p in $mysqlPaths) {
        $found = Get-ChildItem $p -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $mysqlCmd = $found.FullName; break }
    }

    if (-not $mysqlCmd) {
        if (Get-Command mysql -ErrorAction SilentlyContinue) {
            $mysqlCmd = (Get-Command mysql).Source
        }
    }

    if (-not $mysqlCmd) {
        Log "[ERROR] MySQL not found. Install MySQL or XAMPP and try again."
        exit
    }
    Log "[OK] MySQL detected: $mysqlCmd"

    # ------------------------------------------------
    # 3. DATABASE SETUP
    # ------------------------------------------------
    Log "[3/6] Setting up Database"

    Write-Host "Enter your MySQL ROOT password (used only once):" -ForegroundColor Yellow
    $rootPass = Read-Host -AsSecureString
    $rootPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($rootPass)
    )

    $DB_NAME = "ml_db"
    $DB_USER = "intelliroad_user"
    $DB_PASS = -join ((33..126) | Get-Random -Count 16 | ForEach-Object {[char]$_})

    # Create temporary login file for root
    $loginFileRoot = "$PROJECT_DIR\mylogin_root.cnf"
    Set-Content -Path $loginFileRoot -Value "[client]`nuser=root`npassword=$rootPassPlain" -Encoding ASCII

    # Drop and recreate user + DB
    & $mysqlCmd --defaults-extra-file=$loginFileRoot -e "
        CREATE DATABASE IF NOT EXISTS $DB_NAME;
        DROP USER IF EXISTS '$DB_USER'@'localhost';
        CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
        GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
        FLUSH PRIVILEGES;" 2>$null

    Remove-Item $loginFileRoot -Force
    Log "[OK] Database and user created"

    # ------------------------------------------------
    # 4. SCHEMA IMPORT
    # ------------------------------------------------
    Log "[4/6] Importing schema"

    if (-not (Test-Path "sql\schema.sql")) {
        Log "[ERROR] sql\schema.sql missing!"
        exit
    }

    # Create login file for intelliroad_user
    $loginFileUser = "$PROJECT_DIR\mylogin_user.cnf"
    Set-Content -Path $loginFileUser -Value "[client]`nuser=$DB_USER`npassword=$DB_PASS" -Encoding ASCII

    Start-Sleep -Seconds 1
    cmd /c "`"$mysqlCmd`" --defaults-extra-file=$loginFileUser $DB_NAME < sql\schema.sql" 2>$null
    Remove-Item $loginFileUser -Force
    Log "[OK] Schema imported"

    # ------------------------------------------------
    # 5. CONFIG UPDATE
    # ------------------------------------------------
    Log "[5/6] Updating config.yaml"

    if (Test-Path "config.yaml") {
        $cfg = Get-Content "config.yaml" -Raw
        $cfg = $cfg -replace 'user:\s*".*"', "user: ""$DB_USER"""
        $cfg = $cfg -replace 'password:\s*".*"', "password: ""$DB_PASS"""
        $cfg = $cfg -replace 'db:\s*".*"', "db: ""$DB_NAME"""
        Set-Content "config.yaml" $cfg
        Log "[OK] config.yaml updated"
    }

    # ------------------------------------------------
    # 6. BACKEND + FRONTEND SETUP
    # ------------------------------------------------
    Log "[6/6] Backend & Frontend Setup"

    if (Test-Path "venv") { Remove-Item venv -Recurse -Force }

    & $PYTHON -m venv venv
    & ".\venv\Scripts\pip.exe" install --upgrade pip
    & ".\venv\Scripts\pip.exe" install fastapi "uvicorn[standard]" pymysql pyyaml python-multipart | Out-Null

    if (Test-Path "requirements.txt") {
        & ".\venv\Scripts\pip.exe" install -r requirements.txt | Out-Null
    }

    if (Test-Path "road-cost-frontend") {
        Push-Location "road-cost-frontend"
        cmd /c "npm install" | Out-Null
        Pop-Location
        Log "[OK] Frontend installed"
    }

    Log "=== INSTALL COMPLETED SUCCESSFULLY ==="
}
