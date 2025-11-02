# ================================================================
#    Create Development Symlink for Style Engine Addon
#    Run this as Administrator
# ================================================================

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Creating Development Symlink" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$sourcePath = "C:\Coding\STYLEENGINE\scripts\addons\styleengine"
$targetPath = "C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine"

# Check if source exists
if (-not (Test-Path $sourcePath)) {
    Write-Host "ERROR: Source directory not found: $sourcePath" -ForegroundColor Red
    exit 1
}

# Remove existing target if it exists
if (Test-Path $targetPath) {
    Write-Host "Removing existing addon..." -ForegroundColor Yellow
    Remove-Item $targetPath -Recurse -Force
    Write-Host "  Removed." -ForegroundColor Green
}

# Create parent directory if it doesn't exist
$parentDir = Split-Path $targetPath
if (-not (Test-Path $parentDir)) {
    Write-Host "Creating parent directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
}

# Create symbolic link
Write-Host "Creating symbolic link..." -ForegroundColor Green
Write-Host "  From: $targetPath" -ForegroundColor White
Write-Host "  To:   $sourcePath" -ForegroundColor White

try {
    New-Item -ItemType SymbolicLink -Path $targetPath -Target $sourcePath -Force | Out-Null
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host "  SUCCESS!" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Development symlink created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Open Blender 4.4" -ForegroundColor White
    Write-Host "2. Press F3 and type 'Reload Scripts'" -ForegroundColor White
    Write-Host "3. Go to Edit -> Preferences -> Add-ons" -ForegroundColor White
    Write-Host "4. Search for 'Style Engine'" -ForegroundColor White
    Write-Host "5. Enable the addon" -ForegroundColor White
    Write-Host ""
    Write-Host "You can now edit files in:" -ForegroundColor Cyan
    Write-Host "  $sourcePath" -ForegroundColor White
    Write-Host ""
    Write-Host "And changes will appear in Blender after reloading scripts!" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create symlink" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "This script must be run as Administrator." -ForegroundColor Yellow
    Write-Host "Right-click PowerShell -> Run as Administrator" -ForegroundColor Yellow
    exit 1
}

