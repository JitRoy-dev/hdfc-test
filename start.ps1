# AS-03 Backend - Start Script
# Quick script to start the development server

Write-Host "`n=== Starting AS-03 Backend ===" -ForegroundColor Green

# Check if venv exists
if (-not (Test-Path venv)) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run setup.ps1 first:" -ForegroundColor Yellow
    Write-Host "  .\setup.ps1" -ForegroundColor Gray
    exit 1
}

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it:" -ForegroundColor Yellow
    Write-Host "  Copy-Item .env.example .env" -ForegroundColor Gray
    Write-Host "  notepad .env" -ForegroundColor Gray
    exit 1
}

# Start server
Write-Host "✅ Starting development server..." -ForegroundColor Green
Write-Host "Server will be available at:" -ForegroundColor Cyan
Write-Host "  - Homepage: http://localhost:8000" -ForegroundColor White
Write-Host "  - API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - ReDoc: http://localhost:8000/redoc" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop the server`n" -ForegroundColor Yellow

.\venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
