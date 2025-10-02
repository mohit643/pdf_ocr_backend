@echo off
REM PDF Editor - Windows Quick Start Script
REM Save as: start.bat

echo ================================================
echo 🚀 PDF Editor - Quick Start (Windows)
echo ================================================
echo.

REM Check Python
echo 📦 Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python found

REM Check PostgreSQL
echo.
echo 📦 Checking PostgreSQL...
psql --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ PostgreSQL not found
    echo Download from: https://www.postgresql.org/download/windows/
    pause
    exit /b 1
)
echo ✅ PostgreSQL found

REM Backend setup
echo.
echo 🐍 Setting up Backend...
cd backend

REM Create venv if not exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo ✅ Virtual environment created
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
if exist "requirements.txt" (
    echo Installing dependencies...
    pip install -q -r requirements.txt
    echo ✅ Dependencies installed
) else (
    echo ❌ requirements.txt not found
    pause
    exit /b 1
)

REM Check .env file
if not exist ".env" (
    echo ⚠️  .env file not found
    echo Creating .env file...
    (
        echo DATABASE_URL=postgresql://postgres:password@localhost:5432/pdf_editor
        echo REDIS_HOST=localhost
        echo REDIS_PORT=6379
        echo UPLOAD_DIR=uploads
        echo OUTPUT_DIR=outputs
        echo THUMBNAIL_DIR=thumbnails
        echo SECRET_KEY=change-this-secret-key-in-production
        echo HOST=0.0.0.0
        echo PORT=8000
    ) > .env
    echo ✅ .env file created
    echo ⚠️  Please update DATABASE_URL with your PostgreSQL password
)

REM Initialize database
echo.
echo 💾 Initializing database...
python -c "from database import init_db; init_db()" 2>nul
if %errorlevel% equ 0 (
    echo ✅ Database initialized
) else (
    echo ⚠️  Database initialization skipped
)

REM Start backend
echo.
echo 🚀 Starting Backend Server...
echo ================================================
start "Backend" cmd /k "python app.py"
timeout /t 3 /nobreak >nul
echo ✅ Backend running on http://localhost:8000
echo    API Docs: http://localhost:8000/docs

REM Frontend setup
cd ..
if exist "frontend\" (
    echo.
    echo ⚛️  Setting up Frontend...
    cd frontend
    
    REM Install npm dependencies
    if not exist "node_modules\" (
        echo Installing npm dependencies...
        call npm install
        echo ✅ Dependencies installed
    )
    
    echo 🚀 Starting Frontend Server...
    start "Frontend" cmd /k "npm start"
    echo ✅ Frontend running on http://localhost:3000
) else (
    echo ⚠️  Frontend folder not found
)

echo.
echo ================================================
echo ✅ PDF Editor is running!
echo ================================================
echo.
echo 📱 Access Points:
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo 🛑 To stop: Close the Backend and Frontend windows
echo ================================================
echo.

pause   