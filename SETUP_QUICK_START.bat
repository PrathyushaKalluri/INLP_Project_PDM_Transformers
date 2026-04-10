@echo off
REM Quick Start Script for Backend + Frontend
REM Windows PowerShell version: see START_ALL_SERVICES.ps1

echo.
echo ===============================================
echo   NLP Task Manager - Quick Start
echo ===============================================
echo.

REM Check if running from correct directory
if not exist "backend" (
    echo ERROR: Run this script from project root directory
    echo Expected: e:\SEM 2\...\INLP_Project_PDM_Transformers
    pause
    exit /b 1
)

echo [1/4] Checking prerequisites...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Install Node 18+
    start https://nodejs.org/
    pause
    exit /b 1
)
node --version

REM Check MongoDB
mongosh --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: MongoDB not found locally
    echo Install from: https://www.mongodb.com/try/download/community
    echo Or use: docker run -d -p 27017:27017 mongo:latest
    echo.
    pause
)

echo.
echo [2/4] Setting up backend...
echo.

cd backend

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install -q -r requirements.txt

REM Create .env if doesn't exist
if not exist ".env" (
    echo Creating .env file...
    copy .env.example .env >nul
    echo NOTE: Edit backend\.env with your MongoDB URL
)

cd ..

echo.
echo [3/4] Setting up frontend...
echo.

cd kanban-app

REM Install npm dependencies
if not exist "node_modules" (
    echo Installing Node dependencies...
    call npm install
) else (
    echo Node modules already installed
)

REM Create .env.local if doesn't exist
if not exist ".env.local" (
    echo Creating .env.local file...
    (
        echo NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
        echo NEXT_PUBLIC_API_ENDPOINT=http://localhost:8000/api
        echo NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
        echo NEXT_PUBLIC_APP_NAME=Meeting Task Manager
        echo NEXT_PUBLIC_APP_ENV=development
    ) > .env.local
)

cd ..

echo.
echo ===============================================
echo   ✅ Setup Complete!
echo ===============================================
echo.
echo Next steps:
echo.
echo 1. OPEN 3 TERMINALS:
echo.
echo    Terminal 1 (MongoDB):
echo      mongosh
echo.
echo    Terminal 2 (Backend):
echo      cd backend
echo      .\venv\Scripts\activate.ps1
echo      python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
echo.
echo    Terminal 3 (Frontend):
echo      cd kanban-app
echo      npm run dev
echo.
echo 2. OPEN BROWSER:
echo    http://localhost:3000
echo.
echo 3. TEST:
echo    - Upload transcript
echo    - Start processing
echo    - Monitor real-time progress
echo    - View generated tasks
echo.
echo ===============================================
echo.

pause
