Add-Type -Assembly System.IO.Compression.FileSystem
$zipPath = "$PSScriptRoot\styleengine.zip"
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)

Write-Host "ZIP Structure (first 15 entries):"
$zip.Entries | Select-Object -First 15 | ForEach-Object {
    Write-Host "  $($_.FullName)"
}

$zip.Dispose()

Write-Host ""
Write-Host "Checking for styleengine/ directory..."
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
$hasStyleengineDir = $zip.Entries | Where-Object { $_.FullName -like "styleengine/*" }
$zip.Dispose()

if ($hasStyleengineDir) {
    Write-Host "[OK] Correct structure: styleengine/ directory found"
} else {
    Write-Host "[ERROR] Wrong structure: No styleengine/ directory!"
}
