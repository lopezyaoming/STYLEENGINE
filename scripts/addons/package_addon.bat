@echo off
REM ================================================================
REM    Style Engine - Addon Packaging Script (Windows)
REM    Creates a cross-platform ZIP for Blender installation
REM ================================================================

setlocal enabledelayedexpansion

echo ===============================================
echo   Style Engine - Addon Packaging
echo ===============================================
echo.

REM Set paths
set "SOURCE_DIR=%~dp0styleengine"
set "OUTPUT_ZIP=%~dp0styleengine.zip"
set "TEMP_DIR=%TEMP%\styleengine_package_%RANDOM%"
set "TEMP_ADDON=%TEMP_DIR%\styleengine"

REM Check if source directory exists
if not exist "%SOURCE_DIR%" (
    echo ERROR: Source directory not found: %SOURCE_DIR%
    exit /b 1
)

REM Remove old ZIP if it exists
if exist "%OUTPUT_ZIP%" (
    echo Removing old ZIP file...
    del /f /q "%OUTPUT_ZIP%"
)

echo Creating addon package...
echo.

REM Create temporary directory structure
if exist "%TEMP_DIR%" rd /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"
mkdir "%TEMP_ADDON%"

REM Define files to include (core addon files)
set FILES_TO_COPY=__init__.py prefs.py ui_panel.py workspace_setup.py utils.py runcomfy_client.py runcomfy_deployment.py runcomfy_polling.py README.md

REM Copy files
echo Including files:
for %%F in (%FILES_TO_COPY%) do (
    if exist "%SOURCE_DIR%\%%F" (
        copy /y "%SOURCE_DIR%\%%F" "%TEMP_ADDON%\%%F" >nul
        if !errorlevel! equ 0 (
            echo   [+] %%F
        ) else (
            echo   [!] Failed to copy %%F
        )
    ) else (
        echo   [!] %%F ^(not found, skipping^)
    )
)

echo.
echo Excluding:
echo   [-] __pycache__/
echo   [-] *.pyc files
echo   [-] .git/
echo   [-] *.zip files
echo.

REM Create ZIP with forward slashes (macOS-compatible)
echo Creating ZIP archive with forward slashes (cross-platform)...
echo.

REM Create temporary PowerShell script
set "PS_SCRIPT=%TEMP%\create_styleengine_zip_%RANDOM%.ps1"
(
echo Add-Type -Assembly System.IO.Compression.FileSystem
echo Add-Type -Assembly System.IO.Compression
echo $zip = [System.IO.File]::Create('%OUTPUT_ZIP%'^)
echo $archive = New-Object System.IO.Compression.ZipArchive($zip, [System.IO.Compression.ZipArchiveMode]::Create^)
echo Get-ChildItem -Path '%TEMP_ADDON%' -File ^| ForEach-Object {
echo     $entryName = "styleengine/$($_.Name)"
echo     $entry = $archive.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal^)
echo     $entryStream = $entry.Open(^)
echo     $fileStream = [System.IO.File]::OpenRead($_.FullName^)
echo     $fileStream.CopyTo($entryStream^)
echo     $fileStream.Close(^)
echo     $entryStream.Close(^)
echo }
echo $archive.Dispose(^)
echo $zip.Close(^)
) > "%PS_SCRIPT%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set ZIP_RESULT=!errorlevel!

REM Clean up
del /f /q "%PS_SCRIPT%" 2>nul
rd /s /q "%TEMP_DIR%"

if !ZIP_RESULT! neq 0 (
    echo ERROR: Failed to create ZIP archive
    exit /b 1
)

REM Verify ZIP was created
if exist "%OUTPUT_ZIP%" (
    for %%A in ("%OUTPUT_ZIP%") do set "ZIP_SIZE=%%~zA"
    set /a ZIP_SIZE_KB=!ZIP_SIZE! / 1024
    
    echo ===============================================
    echo   ZIP CREATED
    echo ===============================================
    echo.
    echo Package created: %OUTPUT_ZIP%
    echo Size: !ZIP_SIZE_KB! KB
    echo.
    
    REM Run validation if Python is available
    echo Running validation checks...
    echo.
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        python validate_package.py "%OUTPUT_ZIP%"
        set VALIDATION_RESULT=!errorlevel!
    ) else (
        where py >nul 2>nul
        if !errorlevel! equ 0 (
            py validate_package.py "%OUTPUT_ZIP%"
            set VALIDATION_RESULT=!errorlevel!
        ) else (
            echo [!] Python not found in PATH - skipping validation
            echo [!] To validate manually, run:
            echo [!]   python validate_package.py styleengine.zip
            set VALIDATION_RESULT=0
        )
    )
    echo.
    
    if !VALIDATION_RESULT! equ 0 (
        echo ===============================================
        echo   SUCCESS!
        echo ===============================================
        echo.
        echo Installation steps:
        echo 1. Open Blender 4.2+
        echo 2. Edit -^> Preferences -^> Add-ons
        echo 3. Click Install from Disk...
        echo 4. Select: %OUTPUT_ZIP%
        echo 5. Enable the Style Engine addon
        echo.
        echo Cross-platform compatible: Windows, macOS, Linux
        echo.
        echo For macOS testing checklist, see:
        echo   CROSS_PLATFORM_TESTING.md
        echo.
    ) else (
        echo ===============================================
        echo   WARNING: Validation issues found
        echo ===============================================
        echo.
        echo Package created but validation detected issues.
        echo Review the errors above before distribution.
        echo.
    )
) else (
    echo ERROR: Failed to create ZIP package
    exit /b 1
)

endlocal
exit /b 0

