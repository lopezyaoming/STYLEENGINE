# ================================================================
#    Style Engine - Addon Packaging Script
#    Creates a clean ZIP for Blender installation
# ================================================================

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Style Engine - Addon Packaging" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Set paths
$sourceDir = Join-Path $PSScriptRoot "styleengine"
$outputZip = Join-Path $PSScriptRoot "styleengine.zip"

# Check if source directory exists
if (-not (Test-Path $sourceDir)) {
    Write-Host "ERROR: Source directory not found: $sourceDir" -ForegroundColor Red
    exit 1
}

# Remove old ZIP if it exists
if (Test-Path $outputZip) {
    Write-Host "Removing old ZIP file..." -ForegroundColor Yellow
    Remove-Item $outputZip -Force
}

Write-Host "Creating addon package..." -ForegroundColor Green
Write-Host ""

# Get all files to include
$filesToInclude = @(
    "__init__.py",
    "prefs.py",
    "ui_panel.py",
    "workspace_setup.py",
    "utils.py",
    "runcomfy_client.py",
    "runcomfy_deployment.py",
    "runcomfy_polling.py",
    "README.md"
)

# Create temporary directory for clean packaging
$tempDir = Join-Path $env:TEMP "styleengine_package"
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir | Out-Null
$tempStyleEngine = Join-Path $tempDir "styleengine"
New-Item -ItemType Directory -Path $tempStyleEngine | Out-Null

# Copy files
Write-Host "Including files:" -ForegroundColor White
foreach ($file in $filesToInclude) {
    $sourcePath = Join-Path $sourceDir $file
    if (Test-Path $sourcePath) {
        Copy-Item $sourcePath -Destination $tempStyleEngine
        Write-Host "  [+] $file" -ForegroundColor Green
    } else {
        Write-Host "  [!] $file (not found, skipping)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Excluding:" -ForegroundColor White
Write-Host "  [-] __pycache__/" -ForegroundColor DarkGray
Write-Host "  [-] *.pyc files" -ForegroundColor DarkGray
Write-Host "  [-] .git/" -ForegroundColor DarkGray

Write-Host ""

# Create ZIP from temp directory
Compress-Archive -Path $tempStyleEngine -DestinationPath $outputZip -Force

# Clean up temp directory
Remove-Item $tempDir -Recurse -Force

# Verify ZIP was created
if (Test-Path $outputZip) {
    $zipSize = (Get-Item $outputZip).Length / 1KB
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host "  SUCCESS!" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Package created: $outputZip" -ForegroundColor White
    Write-Host "Size: $([math]::Round($zipSize, 2)) KB" -ForegroundColor White
    Write-Host ""
    Write-Host "Installation steps:" -ForegroundColor Yellow
    Write-Host "1. Open Blender 4.2+" -ForegroundColor White
    Write-Host "2. Edit -> Preferences -> Add-ons" -ForegroundColor White
    Write-Host "3. Click Install from Disk..." -ForegroundColor White
    Write-Host "4. Select: $outputZip" -ForegroundColor White
    Write-Host "5. Enable the Style Engine addon" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "ERROR: Failed to create ZIP package" -ForegroundColor Red
    exit 1
}
