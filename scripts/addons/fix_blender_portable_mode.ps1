# Fix Blender Portable Mode - Style Engine Dev Setup
# Resolves HeavyPoly portable config permission issues

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  Fixing Blender Portable Mode Issues" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[!] This script needs Administrator privileges" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please:" -ForegroundColor White
    Write-Host "1. Right-click PowerShell" -ForegroundColor White
    Write-Host "2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "3. Navigate to: C:\Coding\STYLEENGINE\scripts\addons" -ForegroundColor White
    Write-Host "4. Run: .\fix_blender_portable_mode.ps1" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Running with Administrator privileges" -ForegroundColor Green
Write-Host ""

# Paths
$blenderPath = "C:\Program Files\Blender Foundation\Blender 4.4"
$portablePath = Join-Path $blenderPath "portable"
$portableBackup = Join-Path $blenderPath "portable.backup"
$userConfig = "$env:APPDATA\Blender Foundation\Blender\4.4"
$addonsPath = Join-Path $userConfig "scripts\addons"
$sourceAddon = "C:\Coding\STYLEENGINE\scripts\addons\styleengine"
$targetAddon = Join-Path $addonsPath "styleengine"

Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Blender: $blenderPath" -ForegroundColor White
Write-Host "  Portable config: $portablePath" -ForegroundColor White
Write-Host "  User config: $userConfig" -ForegroundColor White
Write-Host ""

# Step 1: Backup portable config
Write-Host "Step 1: Handling portable configuration..." -ForegroundColor Yellow
if (Test-Path $portablePath) {
    Write-Host "  Found portable config folder" -ForegroundColor White
    
    # Check if backup already exists
    if (Test-Path $portableBackup) {
        Write-Host "  Removing old backup..." -ForegroundColor Yellow
        Remove-Item $portableBackup -Recurse -Force
    }
    
    # Rename portable to portable.backup
    Write-Host "  Backing up to: $portableBackup" -ForegroundColor White
    Rename-Item $portablePath $portableBackup -Force
    Write-Host "  [OK] Portable mode disabled (backed up)" -ForegroundColor Green
    Write-Host ""
    Write-Host "  NOTE: Blender will now use standard user config at:" -ForegroundColor Cyan
    Write-Host "        $userConfig" -ForegroundColor White
}
else {
    Write-Host "  [INFO] No portable config found (already using standard mode)" -ForegroundColor Green
}

Write-Host ""

# Step 2: Ensure user config directories exist
Write-Host "Step 2: Setting up user config directories..." -ForegroundColor Yellow
if (-not (Test-Path $userConfig)) {
    Write-Host "  Creating user config directory..." -ForegroundColor White
    New-Item -ItemType Directory -Path $userConfig -Force | Out-Null
}

if (-not (Test-Path $addonsPath)) {
    Write-Host "  Creating addons directory..." -ForegroundColor White
    New-Item -ItemType Directory -Path $addonsPath -Force | Out-Null
}
Write-Host "  [OK] User directories ready" -ForegroundColor Green
Write-Host ""

# Step 3: Verify source addon exists
Write-Host "Step 3: Checking source addon..." -ForegroundColor Yellow
if (-not (Test-Path $sourceAddon)) {
    Write-Host "  [ERROR] Source addon not found!" -ForegroundColor Red
    Write-Host "          Expected: $sourceAddon" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] Source addon found" -ForegroundColor Green
Write-Host ""

# Step 4: Remove old symlink/installation if exists
Write-Host "Step 4: Cleaning up old installation..." -ForegroundColor Yellow
if (Test-Path $targetAddon) {
    $item = Get-Item $targetAddon
    if ($item.Attributes -match "ReparsePoint") {
        Write-Host "  Removing old symlink..." -ForegroundColor Yellow
    }
    else {
        Write-Host "  Removing old installation..." -ForegroundColor Yellow
    }
    Remove-Item $targetAddon -Recurse -Force
    Write-Host "  [OK] Cleaned up" -ForegroundColor Green
}
else {
    Write-Host "  [INFO] No existing installation" -ForegroundColor White
}
Write-Host ""

# Step 5: Create new symlink
Write-Host "Step 5: Creating development symlink..." -ForegroundColor Yellow
Write-Host "  From: $targetAddon" -ForegroundColor White
Write-Host "  To:   $sourceAddon" -ForegroundColor White

try {
    New-Item -ItemType SymbolicLink -Path $targetAddon -Target $sourceAddon -Force | Out-Null
    Write-Host "  [OK] Symlink created successfully" -ForegroundColor Green
}
catch {
    Write-Host "  [ERROR] Failed to create symlink" -ForegroundColor Red
    Write-Host "          $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Step 6: Verify symlink
Write-Host "Step 6: Verifying symlink..." -ForegroundColor Yellow
$symlinkTarget = (Get-Item $targetAddon).Target
if ($symlinkTarget -eq $sourceAddon) {
    Write-Host "  [OK] Symlink verified and pointing to correct location" -ForegroundColor Green
}
else {
    Write-Host "  [WARN] Symlink may not be correct" -ForegroundColor Yellow
    Write-Host "         Expected: $sourceAddon" -ForegroundColor White
    Write-Host "         Got: $symlinkTarget" -ForegroundColor White
}

# Verify files are accessible
$testFile = Join-Path $targetAddon "__init__.py"
if (Test-Path $testFile) {
    Write-Host "  [OK] Addon files accessible through symlink" -ForegroundColor Green
}
else {
    Write-Host "  [WARN] Cannot access addon files" -ForegroundColor Yellow
}
Write-Host ""

# Step 7: Copy HeavyPoly config if needed
Write-Host "Step 7: Checking for HeavyPoly configuration..." -ForegroundColor Yellow
if (Test-Path $portableBackup) {
    $heavypolyStartup = Join-Path $portableBackup "config\startup.blend"
    $heavypolyPrefs = Join-Path $portableBackup "config\userpref.blend"
    
    if ((Test-Path $heavypolyStartup) -or (Test-Path $heavypolyPrefs)) {
        Write-Host "  Found HeavyPoly config files" -ForegroundColor White
        Write-Host ""
        $copy = Read-Host "  Copy HeavyPoly config to user directory? (y/n)"
        
        if ($copy -eq 'y' -or $copy -eq 'Y') {
            $configPath = Join-Path $userConfig "config"
            if (-not (Test-Path $configPath)) {
                New-Item -ItemType Directory -Path $configPath -Force | Out-Null
            }
            
            if (Test-Path $heavypolyStartup) {
                Copy-Item $heavypolyStartup $configPath -Force
                Write-Host "  [OK] Copied startup.blend" -ForegroundColor Green
            }
            if (Test-Path $heavypolyPrefs) {
                Copy-Item $heavypolyPrefs $configPath -Force
                Write-Host "  [OK] Copied userpref.blend" -ForegroundColor Green
            }
        }
        else {
            Write-Host "  [INFO] Skipped HeavyPoly config copy" -ForegroundColor White
            Write-Host "  NOTE: You can manually copy files from:" -ForegroundColor Cyan
            Write-Host "        $portableBackup\config" -ForegroundColor White
        }
    }
    else {
        Write-Host "  [INFO] No HeavyPoly config found" -ForegroundColor White
    }
}
else {
    Write-Host "  [INFO] No backup to check" -ForegroundColor White
}
Write-Host ""

# Final summary
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "What was done:" -ForegroundColor Yellow
Write-Host "  1. Disabled portable mode (backed up to portable.backup)" -ForegroundColor White
Write-Host "  2. Set up standard user config directory" -ForegroundColor White
Write-Host "  3. Created development symlink for Style Engine" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Start Blender 4.4" -ForegroundColor White
Write-Host "  2. Go to Edit -> Preferences -> Add-ons" -ForegroundColor White
Write-Host "  3. Search for 'Style Engine'" -ForegroundColor White
Write-Host "  4. Enable the addon (checkbox)" -ForegroundColor White
Write-Host ""
Write-Host "Development workflow:" -ForegroundColor Cyan
Write-Host "  - Edit files in: C:\Coding\STYLEENGINE\scripts\addons\styleengine" -ForegroundColor White
Write-Host "  - In Blender: Press F3 -> 'Reload Scripts' to see changes" -ForegroundColor White
Write-Host "  - Or restart Blender to reload the addon" -ForegroundColor White
Write-Host ""
Write-Host "Troubleshooting:" -ForegroundColor Cyan
Write-Host "  - If addon doesn't appear: Check Blender console for errors" -ForegroundColor White
Write-Host "  - If HeavyPoly settings missing: Copy from portable.backup\config" -ForegroundColor White
Write-Host "  - Config location: $userConfig" -ForegroundColor Gray
Write-Host ""
Write-Host "To restore portable mode later:" -ForegroundColor DarkGray
Write-Host "  Rename portable.backup back to portable" -ForegroundColor DarkGray
Write-Host ""

Read-Host "Press Enter to exit"
