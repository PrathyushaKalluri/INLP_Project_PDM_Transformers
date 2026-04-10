# Quick Start Script - PowerShell Version
# Usage: .\START_SERVICES.ps1
# Starts all backend, frontend, and MongoDB services

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗"
Write-Host "║   🚀 NLP Task Manager - START SERVICES (PowerShell)        ║"
Write-Host "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

# Color functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error_ { Write-Host $args -ForegroundColor Red }
function Write-Warning_ { Write-Host $args -ForegroundColor Yellow }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

# Check if running from correct directory
if (-not (Test-Path "backend") -or -not (Test-Path "kanban-app")) {
    Write-Error_ "❌ ERROR: Run this script from project root directory"
    Write-Error_ "Expected to find: backend/ and kanban-app/ folders"
    exit 1
}

# ╔════════════════════════════════════════════════════════════╗
# ║ PREREQUISITES CHECK
# ╚════════════════════════════════════════════════════════════╝

Write-Info "📋 Checking prerequisites..."
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Success "✓ Python: $pythonVersion"
} catch {
    Write-Error_ "✗ Python not found!"
    Write-Error_ "  Install from: https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Success "✓ Node.js: $nodeVersion"
} catch {
    Write-Error_ "✗ Node.js not found!"
    Write-Error_ "  Install from: https://nodejs.org/"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check MongoDB
try {
    $mongoVersion = mongosh --version 2>&1
    Write-Success "✓ MongoDB: $mongoVersion"
} catch {
    Write-Warning_ "⚠ MongoDB not detected locally"
    Write-Warning_ "  Options:"
    Write-Warning_ "    1. Install: https://www.mongodb.com/try/download/community"
    Write-Warning_ "    2. Docker: docker run -d -p 27017:27017 mongo:latest"
    Write-Warning_ "    3. MongoDB Atlas: Use cloud connection in .env"
    Write-Host ""
}

Write-Host ""

# ╔════════════════════════════════════════════════════════════╗
# ║ BACKEND SETUP
# ╚════════════════════════════════════════════════════════════╝

Write-Info "⚙️  Setting up backend..."

Push-Location backend

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "  Creating Python virtual environment..."
    python -m venv venv
    Write-Success "  ✓ Virtual environment created"
} else {
    Write-Success "  ✓ Virtual environment exists"
}

# Activate virtual environment
Write-Host "  Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"
Write-Success "  ✓ Virtual environment activated"

# Install dependencies
Write-Host "  Installing Python dependencies..."
pip install -q -r requirements.txt
Write-Success "  ✓ Dependencies installed"

# Create .env if not exists
if (-not (Test-Path ".env")) {
    Write-Host "  Creating .env file from template..."
    Copy-Item .env.example .env
    Write-Success "  ✓ .env created (edit if needed)"
} else {
    Write-Success "  ✓ .env already exists"
}

Pop-Location

Write-Host ""

# ╔════════════════════════════════════════════════════════════╗
# ║ FRONTEND SETUP
# ╚════════════════════════════════════════════════════════════╝

Write-Info "⚙️  Setting up frontend..."

Push-Location kanban-app

# Install npm dependencies
if (-not (Test-Path "node_modules")) {
    Write-Host "  Installing npm dependencies..."
    npm install
    Write-Success "  ✓ Dependencies installed"
} else {
    Write-Success "  ✓ node_modules exists"
}

# Create .env.local if not exists
if (-not (Test-Path ".env.local")) {
    Write-Host "  Creating .env.local file..."
    @"
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_ENDPOINT=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_APP_NAME=Meeting Task Manager
NEXT_PUBLIC_APP_ENV=development
"@ | Out-File -Encoding UTF8 .env.local
    Write-Success "  ✓ .env.local created"
} else {
    Write-Success "  ✓ .env.local already exists"
}

Pop-Location

Write-Host ""

# ╔════════════════════════════════════════════════════════════╗
# ║ INSTRUCTIONS
# ╚════════════════════════════════════════════════════════════╝

Write-Success "╔════════════════════════════════════════════════════════════╗"
Write-Success "║  ✅ SETUP COMPLETE - READY TO START SERVICES              ║"
Write-Success "╚════════════════════════════════════════════════════════════╝"

Write-Host ""
Write-Host "📖 NEXT STEPS:"
Write-Host ""
Write-Host "You need to open 3 SEPARATE TERMINALS:"
Write-Host ""

Write-Warning_ "🔧 TERMINAL 1 - MongoDB:"
Write-Host "   mongosh"
Write-Host ""

Write-Warning_ "🔧 TERMINAL 2 - Backend API:"
Write-Host "   cd backend"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host "   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
Write-Host ""
Write-Host "   Expected: 'Application startup complete' ✓"
Write-Host "   Backend: http://localhost:8000"
Write-Host "   Docs: http://localhost:8000/docs"
Write-Host ""

Write-Warning_ "🔧 TERMINAL 3 - Frontend:"
Write-Host "   cd kanban-app"
Write-Host "   npm run dev"
Write-Host ""
Write-Host "   Expected: 'Local: http://localhost:3000' ✓"
Write-Host ""

Write-Success "🌐 OPEN BROWSER:"
Write-Host "   http://localhost:3000"
Write-Host ""

Write-Success "✨ TEST WORKFLOW:"
Write-Host "   1. Upload transcript"
Write-Host "   2. Start processing"
Write-Host "   3. Watch real-time progress (WebSocket)"
Write-Host "   4. View generated tasks"
Write-Host "   5. Test multi-tab sync (open 2nd tab)"
Write-Host "   6. Refresh (verify data persistence)"
Write-Host ""

Write-Host ""
Write-Info "⚡ QUICK COMMANDS:"
Write-Host ""
Write-Host "   Check backend health:      curl http://localhost:8000/docs"
Write-Host "   Check frontend:            curl http://localhost:3000"
Write-Host "   View backend logs:         (see Terminal 2)"
Write-Host "   View frontend logs:        (see Terminal 3)"
Write-Host ""

Write-Host ""
Write-Info "📚 FULL DOCUMENTATION:"
Write-Host "   See: RUN_AND_TEST_GUIDE.md"
Write-Host "   See: COMPREHENSIVE_QA_TEST_PLAN.md"
Write-Host ""

Write-Host ""
Write-Success "╔════════════════════════════════════════════════════════════╗"
Write-Success "║  Ready to start? Open 3 terminals and follow the steps!  ║"
Write-Success "╚════════════════════════════════════════════════════════════╝"
Write-Host ""

Read-Host "Press Enter to continue"
