@echo off
REM Start MongoDB Service on Windows
REM Run as Administrator

echo.
echo ==================================================
echo    MongoDB Service Launcher
echo ==================================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo.
    echo Steps to run as Administrator:
    echo 1. Press Windows Key + S
    echo 2. Type "cmd"
    echo 3. Right-click Command Prompt
    echo 4. Click "Run as Administrator"
    echo 5. Navigate to this folder and run: start_mongodb.bat
    echo.
    pause
    exit /b 1
)

REM Try to start MongoDB service
echo Starting MongoDB service...
net start MongoDB

if %errorlevel% equ 0 (
    echo.
    echo ✓ MongoDB service started successfully!
    echo.
    echo Connecting to MongoDB with mongosh...
    echo.
    call mongosh
    echo.
    echo ✓ MongoDB terminal session closed
) else (
    echo.
    echo ✗ Failed to start MongoDB service
    echo.
    echo MongoDB might not be installed. Visit:
    echo https://www.mongodb.com/try/download/community
    echo.
)

pause
