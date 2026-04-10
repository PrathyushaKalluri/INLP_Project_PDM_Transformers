# Start MongoDB on Windows
# Run this script as Administrator to start MongoDB service

Write-Host "🚀 Starting MongoDB..." -ForegroundColor Green

# Check if MongoDB service exists
$mongoService = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue

if ($mongoService) {
    Write-Host "✓ MongoDB service found" -ForegroundColor Green
    
    # Check if it's already running
    if ($mongoService.Status -eq "Running") {
        Write-Host "✓ MongoDB is already running on localhost:27017" -ForegroundColor Green
    } else {
        Write-Host "Starting MongoDB service..." -ForegroundColor Yellow
        Start-Service -Name "MongoDB"
        Start-Sleep -Seconds 2
        Write-Host "✓ MongoDB started successfully" -ForegroundColor Green
    }
} else {
    Write-Host "✗ MongoDB service not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "MongoDB is not installed as a Windows service." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Quick installation options:" -ForegroundColor Cyan
    Write-Host "1. MongoDB Compass (easiest): https://www.mongodb.com/products/compass" -ForegroundColor White
    Write-Host "2. MongoDB Community: https://www.mongodb.com/try/download/community" -ForegroundColor White
    Write-Host ""
    Write-Host "After installation, this script will work." -ForegroundColor Yellow
    exit 1
}

# Test connection with mongosh
Write-Host ""
Write-Host "Testing connection with mongosh..." -ForegroundColor Cyan
Write-Host "Type 'exit' to close mongosh and return here" -ForegroundColor Gray
Write-Host ""

mongosh

Write-Host ""
Write-Host "✓ MongoDB connection test complete" -ForegroundColor Green
