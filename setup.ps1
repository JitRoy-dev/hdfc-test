# AS-03 Backend - Quick Setup Script
# Run this script to set up the project from scratch

Write-Host "`n=== AS-03 Backend Setup ===" -ForegroundColor Green
Write-Host "This script will set up your development environment`n" -ForegroundColor Cyan

# Check Python
Write-Host "Step 1: Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.10+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}

# Remove old venv
Write-Host "`nStep 2: Cleaning up old virtual environment..." -ForegroundColor Yellow
if (Test-Path venv) {
    Remove-Item -Recurse -Force venv -ErrorAction SilentlyContinue
    Write-Host "✅ Old virtual environment removed" -ForegroundColor Green
} else {
    Write-Host "✅ No old virtual environment found" -ForegroundColor Green
}

# Create new venv
Write-Host "`nStep 3: Creating new virtual environment..." -ForegroundColor Yellow
python -m venv venv
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Virtual environment created successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

# Upgrade pip
Write-Host "`nStep 4: Upgrading pip..." -ForegroundColor Yellow
.\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ pip upgraded successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  pip upgrade failed, continuing anyway..." -ForegroundColor Yellow
}

# Install dependencies
Write-Host "`nStep 5: Installing dependencies..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ All dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Verify installation
Write-Host "`nStep 6: Verifying installation..." -ForegroundColor Yellow
$packages = @("fastapi", "uvicorn", "authlib", "pytest")
$allInstalled = $true
foreach ($package in $packages) {
    $installed = .\venv\Scripts\python.exe -m pip show $package 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $package installed" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $package NOT installed" -ForegroundColor Red
        $allInstalled = $false
    }
}

if (-not $allInstalled) {
    Write-Host "`n❌ Some packages failed to install" -ForegroundColor Red
    exit 1
}

# Copy .env if not exists
Write-Host "`nStep 7: Setting up environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "✅ .env file created from template" -ForegroundColor Green
    Write-Host "⚠️  IMPORTANT: Edit .env with your Keycloak settings!" -ForegroundColor Yellow
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

# Test import
Write-Host "`nStep 8: Testing application import..." -ForegroundColor Yellow
$testResult = .\venv\Scripts\python.exe -c "from app.main import app; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Application imports successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Application import failed" -ForegroundColor Red
    Write-Host $testResult -ForegroundColor Red
    exit 1
}

# Done
Write-Host "`n=== Setup Complete! ===" -ForegroundColor Green
Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env file with your Keycloak settings:" -ForegroundColor White
Write-Host "     notepad .env" -ForegroundColor Gray
Write-Host "`n  2. Activate virtual environment:" -ForegroundColor White
Write-Host "     .\venv\Scripts\activate" -ForegroundColor Gray
Write-Host "`n  3. Start development server:" -ForegroundColor White
Write-Host "     uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host "`n  4. Open in browser:" -ForegroundColor White
Write-Host "     http://localhost:8000" -ForegroundColor Gray
Write-Host "     http://localhost:8000/docs (API documentation)" -ForegroundColor Gray
Write-Host "`n✨ Happy coding!" -ForegroundColor Green
