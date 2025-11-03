# ================================================================
#    Style Engine - POSIX-Compatible ZIP Packaging (macOS Fix)
#    Creates ZIP with forward slashes for cross-platform compatibility
# ================================================================

$ErrorActionPreference = "Stop"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Style Engine - POSIX ZIP Packaging" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Paths
$SourceDir = Join-Path $PSScriptRoot "styleengine"
$OutputZip = Join-Path $PSScriptRoot "styleengine.zip"

# Check source directory exists
if (-not (Test-Path $SourceDir)) {
    Write-Host "ERROR: Source directory not found: $SourceDir" -ForegroundColor Red
    exit 1
}

# Remove old ZIP
if (Test-Path $OutputZip) {
    Write-Host "Removing old ZIP..." -ForegroundColor Yellow
    Remove-Item $OutputZip -Force
}

Write-Host "Creating ZIP with POSIX paths (forward slashes)..." -ForegroundColor Green
Write-Host ""

# Use .NET to create ZIP with proper path separators
Add-Type -Assembly System.IO.Compression.FileSystem
Add-Type -Assembly System.IO.Compression

# Create ZIP file
$zip = [System.IO.Compression.ZipFile]::Open($OutputZip, 'Create')

try {
    # Get all files to include
    $files = Get-ChildItem -Path $SourceDir -Recurse -File | Where-Object {
        $_.Extension -ne '.pyc' -and 
        $_.DirectoryName -notlike '*__pycache__*' -and
        $_.Name -ne '.DS_Store'
    }
    
    foreach ($file in $files) {
        # Get relative path from source directory
        $relativePath = $file.FullName.Substring($SourceDir.Length + 1)
        
        # Convert to POSIX path (forward slashes)
        $zipPath = "styleengine/" + $relativePath.Replace('\', '/')
        
        Write-Host "  [+] $zipPath" -ForegroundColor Gray
        
        # Add file to ZIP with POSIX path
        $entry = $zip.CreateEntry($zipPath, 'Optimal')
        $entryStream = $entry.Open()
        $fileStream = [System.IO.File]::OpenRead($file.FullName)
        
        $fileStream.CopyTo($entryStream)
        
        $fileStream.Close()
        $entryStream.Close()
    }
    
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "  SUCCESS!" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Package created: $OutputZip" -ForegroundColor White
    Write-Host "Size: $([Math]::Round((Get-Item $OutputZip).Length / 1KB)) KB" -ForegroundColor White
    Write-Host ""
    Write-Host "Paths use FORWARD SLASHES for macOS compatibility" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    exit 1
} finally {
    $zip.Dispose()
}

