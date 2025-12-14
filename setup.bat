@echo off
REM ============================================================
REM Road Cost Predictor - First-Time Setup (Improved)
REM ============================================================

color 0B
title Road Cost Predictor - Setup

echo.
echo ============================================================
echo    ROAD COST PREDICTOR - FIRST-TIME SETUP
echo ============================================================
echo.
echo This script will:
echo   1. Check all prerequisites
echo   2. Create virtual environment
echo   3. Install Python dependencies from requirements.txt
echo   4. Install Node.js dependencies
echo   5. Setup database schema
echo   6. Seed material prices
echo   7. Verify ML model
echo.
echo This will take 5-10 minutes...
echo.
pause

REM Get the directory where the script is located
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

echo.
echo ============================================================
echo [STEP 1/8] Checking Prerequisites
echo ============================================================

REM Check Python
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)
python --version
echo [OK] Python found

REM Check pip
echo.
echo Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed
    pause
    exit /b 1
)
echo [OK] pip found

REM Check Node.js
echo.
echo Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo [OK] Node.js found

REM Check npm
echo.
echo Checking npm...
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is not installed
    pause
    exit /b 1
)
npm --version
echo [OK] npm found

REM Check MySQL
echo.
echo Checking MySQL...
mysql --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] MySQL CLI not found in PATH
    echo Please make sure MySQL server is running
    timeout /t 3 >nul
) else (
    mysql --version
    echo [OK] MySQL found
)

REM Check requirements.txt
echo.
echo Checking requirements.txt...
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found in project root!
    echo Please ensure requirements.txt exists
    pause
    exit /b 1
)
echo [OK] requirements.txt found

REM Check frontend folder
echo.
echo Checking frontend folder...
if not exist "road-cost-frontend" (
    echo [ERROR] road-cost-frontend directory not found!
    pause
    exit /b 1
)
echo [OK] Frontend folder found

REM Check package.json
if not exist "road-cost-frontend\package.json" (
    echo [ERROR] package.json not found in road-cost-frontend!
    pause
    exit /b 1
)
echo [OK] package.json found

echo.
echo ============================================================
echo [STEP 2/8] Creating Virtual Environment
echo ============================================================

if exist "venv" (
    echo Virtual environment already exists
    echo [OK] Using existing virtual environment
) else (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated

echo.
echo ============================================================
echo [STEP 3/8] Upgrading pip
echo ============================================================

python -m pip install --upgrade pip
echo [OK] pip upgraded

echo.
echo ============================================================
echo [STEP 4/8] Installing Python Dependencies
echo ============================================================
echo This may take 5-10 minutes depending on your internet speed...
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo.
echo [OK] Python dependencies installed successfully

echo.
echo ============================================================
echo [STEP 5/8] Installing Frontend Dependencies
echo ============================================================
echo This may take 3-5 minutes...
echo.

cd road-cost-frontend

if exist "node_modules" (
    echo node_modules folder already exists
    echo Verifying react-scripts installation...
    
    if exist "node_modules\react-scripts" (
        echo [OK] react-scripts found, using existing installation
    ) else (
        echo [WARNING] react-scripts not found, reinstalling...
        rmdir /s /q node_modules 2>nul
        call npm install
        if errorlevel 1 (
            echo [ERROR] Failed to install frontend dependencies
            cd ..
            pause
            exit /b 1
        )
    )
) else (
    echo Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
    echo [OK] Frontend dependencies installed
)

REM Verify critical packages
echo.
echo Verifying critical packages...
if not exist "node_modules\react" (
    echo [ERROR] React not installed!
    cd ..
    pause
    exit /b 1
)
echo [OK] React installed

if not exist "node_modules\react-scripts" (
    echo [ERROR] react-scripts not installed!
    echo Attempting manual installation...
    call npm install react-scripts
    if errorlevel 1 (
        echo [ERROR] Failed to install react-scripts
        cd ..
        pause
        exit /b 1
    )
)
echo [OK] react-scripts installed

if not exist "node_modules\react-router-dom" (
    echo [WARNING] react-router-dom not found, installing...
    call npm install react-router-dom
)
echo [OK] react-router-dom installed

if not exist "node_modules\axios" (
    echo [WARNING] axios not found, installing...
    call npm install axios
)
echo [OK] axios installed

cd ..

echo.
echo [OK] All frontend dependencies verified

echo.
echo ============================================================
echo [STEP 6/8] Setting Up Database
echo ============================================================

REM Check if config.yaml exists
if not exist "config.yaml" (
    echo [ERROR] config.yaml not found!
    echo.
    echo Please create config.yaml with this content:
    echo.
    echo mysql:
    echo   host: localhost
    echo   user: root
    echo   password: "your_mysql_password"
    echo   db: road_costs
    echo.
    echo training:
    echo   model_path: models/xgb_model.joblib
    echo   scaler_path: models/scaler.joblib
    echo.
    pause
    exit /b 1
)
echo [OK] config.yaml found

echo.
echo Creating database 'road_costs' if not exists...
echo Please enter your MySQL root password when prompted
echo.

mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS road_costs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if errorlevel 1 (
    echo [ERROR] Failed to create database
    echo Please check your MySQL credentials in config.yaml
    pause
    exit /b 1
)
echo [OK] Database created

echo.
echo Applying database schema...
if not exist "sql\schema.sql" (
    echo [ERROR] sql\schema.sql not found!
    pause
    exit /b 1
)

mysql -u root -p road_costs < sql\schema.sql
if errorlevel 1 (
    echo [ERROR] Failed to apply schema
    pause
    exit /b 1
)
echo [OK] Schema applied successfully

echo.
echo ============================================================
echo [STEP 7/8] Seeding Material Prices
echo ============================================================

python -m backend.utils.inflation
if errorlevel 1 (
    echo [ERROR] Failed to seed materials
    echo Please check your database connection in config.yaml
    pause
    exit /b 1
)

echo [OK] Materials and prices seeded successfully

echo.
echo ============================================================
echo [STEP 8/8] Verifying ML Model
echo ============================================================

REM Create models directory if it doesn't exist
if not exist "models" (
    echo Creating models directory...
    mkdir models
)

if exist "models\xgb_model.joblib" (
    if exist "models\scaler.joblib" (
        echo [OK] ML model files found
        echo   - xgb_model.joblib
        echo   - scaler.joblib
    ) else (
        echo [WARNING] scaler.joblib missing
        goto TRAIN_MODEL
    )
) else (
    echo [WARNING] ML model not found
    goto TRAIN_MODEL
)

goto SETUP_COMPLETE

:TRAIN_MODEL
echo.
echo ML model files are missing. The model needs to be trained.
echo This requires training data from the tenders table.
echo.
set /p TRAIN="Do you want to train the model now? (y/n): "
if /i "%TRAIN%"=="y" (
    echo.
    echo Checking for training data...
    python -c "from backend.database import get_conn; conn = get_conn(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) as count FROM ml_training_data'); result = cur.fetchone(); print(f'Training records: {result[\"count\"]}'); exit(0 if result['count'] > 0 else 1)"
    
    if errorlevel 1 (
        echo.
        echo [WARNING] No training data found in ml_training_data table
        echo You need to either:
        echo   1. Run the scraper to collect tender data
        echo   2. Prepare training data: python -m backend.ml.prepare_ml_training_data
        echo   3. Then train the model: python -m backend.ml.train_model
        echo.
        echo The application will work but predictions will use fallback calculations
        echo until the model is trained.
    ) else (
        echo.
        echo Training model... This may take 2-5 minutes...
        python -m backend.ml.train_model
        if errorlevel 1 (
            echo [ERROR] Model training failed
            echo The application will work but use fallback calculations
        ) else (
            echo [OK] Model trained successfully
        )
    )
) else (
    echo.
    echo [INFO] Skipping model training
    echo The application will work but predictions will use fallback calculations
    echo You can train the model later by running:
    echo   python -m backend.ml.train_model
)

:SETUP_COMPLETE
echo.
echo ============================================================
echo    SETUP COMPLETE!
echo ============================================================
echo.
echo Installation Summary:
echo   [x] Python environment ready
echo   [x] All dependencies installed
echo   [x] Database created and configured
echo   [x] Materials and prices seeded
if exist "models\xgb_model.joblib" (
    echo   [x] ML model ready
) else (
    echo   [ ] ML model not trained ^(will use fallback^)
)
echo.
echo ============================================================
echo    VERIFICATION
echo ============================================================
echo.
echo Checking installations...
echo.

REM Verify Python packages
call venv\Scripts\activate.bat
python -c "import fastapi; import uvicorn; import xgboost; print('[OK] Key Python packages installed')" 2>nul
if errorlevel 1 (
    echo [WARNING] Some Python packages may not be installed correctly
)

REM Verify frontend
if exist "road-cost-frontend\node_modules\react-scripts" (
    echo [OK] Frontend dependencies verified
) else (
    echo [ERROR] Frontend dependencies missing!
)

echo.
echo ============================================================
echo    HOW TO START THE APPLICATION
echo ============================================================
echo.
echo 1. Double-click "START.bat"
echo 2. Wait for both servers to start (10-15 seconds)
echo 3. Browser will open automatically at http://localhost:3000
echo.
echo ============================================================
echo    FIRST TIME LOGIN
echo ============================================================
echo.
echo 1. Click "Create Account"
echo 2. Register a new user
echo 3. Login with your credentials
echo 4. Start creating road cost predictions!
echo.
echo ============================================================
echo.
echo For help, see README.txt
echo.
echo ============================================================
echo.
pause