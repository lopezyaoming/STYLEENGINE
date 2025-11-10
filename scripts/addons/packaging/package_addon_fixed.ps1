# ================================================================
#    Style Engine - Cross-Platform Addon Packaging (PowerShell)
#    Creates ZIP with forward slashes for macOS compatibility
# ================================================================

$ErrorActionPreference = "Stop"

Write-Host "=============================================="
Write-Host "  Style Engine - Addon Packaging"
Write-Host "=============================================="
Write-Host ""

# Paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDir = Join-Path $scriptDir "styleengine"
$outputZip = Join-Path $scriptDir "styleengine.zip"

# Files to include
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

# Check source directory
if (-not (Test-Path $sourceDir)) {
    Write-Host "ERROR: Source directory not found: $sourceDir" -ForegroundColor Red
    exit 1
}

# Remove old ZIP
if (Test-Path $outputZip) {
    Write-Host "Removing old ZIP file..."
    Remove-Item $outputZip -Force
}

Write-Host "Creating addon package..."
Write-Host ""

# Load ZIP assembly
Add-Type -Assembly System.IO.Compression.FileSystem
Add-Type -Assembly System.IO.Compression

# Create ZIP manually with forward slashes
try {
    $zipStream = [System.IO.File]::Create($outputZip)
    $zip = New-Object System.IO.Compression.ZipArchive($zipStream, [System.IO.Compression.ZipArchiveMode]::Create)
    
    Write-Host "Including files:"
    $missingFiles = @()
    
    foreach ($file in $filesToInclude) {
        $sourceFile = Join-Path $sourceDir $file
        
        if (Test-Path $sourceFile) {
            # CRITICAL: Use forward slashes for cross-platform compatibility
            $entryName = "styleengine/$file"
            
            # Add file to ZIP with forward slash path
            $entry = $zip.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
            $entryStream = $entry.Open()
            $fileStream = [System.IO.File]::OpenRead($sourceFile)
            $fileStream.CopyTo($entryStream)
            $fileStream.Close()
            $entryStream.Close()
            
            Write-Host "  [+] $file"
        }
        else {
            Write-Host "  [!] $file (not found, skipping)" -ForegroundColor Yellow
            $missingFiles += $file
        }
    }
    
    $zip.Dispose()
    $zipStream.Close()
    
    Write-Host ""
    Write-Host "Excluding:"
    Write-Host "  [-] __pycache__/"
    Write-Host "  [-] *.pyc files"
    Write-Host "  [-] .git/"
    Write-Host ""
    
    # Get ZIP size
    $zipInfo = Get-Item $outputZip
    $zipSizeKB = [math]::Round($zipInfo.Length / 1KB, 0)
    
    Write-Host "=============================================="
    Write-Host "  ZIP CREATED"
    Write-Host "=============================================="
    Write-Host ""
    Write-Host "Package created: $outputZip"
    Write-Host "Size: $zipSizeKB KB"
    Write-Host ""
    
    # Verify structure
    Write-Host "Verifying ZIP structure..."
    $verifyZip = [System.IO.Compression.ZipFile]::OpenRead($outputZip)
    $entries = $verifyZip.Entries
    
    Write-Host "  Entries in ZIP: $($entries.Count)"
    Write-Host "  Sample entries:"
    
    $entries | Select-Object -First 5 | ForEach-Object {
        Write-Host "    - $($_.FullName)"
    }
    
    # Check for backslashes
    $hasBackslashes = $entries | Where-Object { $_.FullName -match '\\' }
    $hasForwardSlashes = $entries | Where-Object { $_.FullName -match 'styleengine/' }
    
    $verifyZip.Dispose()
    
    Write-Host ""
    if ($hasForwardSlashes -and -not $hasBackslashes) {
        Write-Host "  [OK] Proper structure with forward slashes" -ForegroundColor Green
    }
    elseif ($hasBackslashes) {
        Write-Host "  [ERROR] ZIP contains backslashes! (macOS will fail)" -ForegroundColor Red
        exit 1
    }
    else {
        Write-Host "  [WARNING] Structure may be incorrect" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "=============================================="
    Write-Host "  SUCCESS!"
    Write-Host "=============================================="
    Write-Host ""
    Write-Host "Installation steps:"
    Write-Host "1. Open Blender 4.2+"
    Write-Host "2. Edit -> Preferences -> Add-ons"
    Write-Host "3. Click Install from Disk..."
    Write-Host "4. Select: $outputZip"
    Write-Host "5. Enable the Style Engine addon"
    Write-Host ""
    Write-Host "Cross-platform compatible: Windows, macOS, Linux" -ForegroundColor Green
    Write-Host ""
    
    if ($missingFiles.Count -gt 0) {
        Write-Host "WARNING: $($missingFiles.Count) file(s) were missing:" -ForegroundColor Yellow
        $missingFiles | ForEach-Object { Write-Host "  - $_" }
        Write-Host ""
    }
}
catch {
    Write-Host "ERROR: Failed to create ZIP" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

exit 0

