@echo off
REM ================================================================
REM    Style Engine - Advanced Addon Packaging Script
REM    Robust, scalable, cross-platform compatible
REM ================================================================

setlocal enabledelayedexpansion

REM ================================================================
REM Configuration
REM ================================================================
set "SCRIPT_DIR=%~dp0"
set "SOURCE_DIR=%SCRIPT_DIR%styleengine"
set "OUTPUT_ZIP=%SCRIPT_DIR%styleengine.zip"
set "CONFIG_FILE=%SCRIPT_DIR%package_config.txt"
set "TEMP_BASE=%TEMP%\styleengine_package_%RANDOM%"
set "TEMP_ADDON=%TEMP_BASE%\styleengine"
set "LOG_FILE=%SCRIPT_DIR%package_log.txt"

REM Colors disabled for compatibility
set "COLOR_CYAN="
set "COLOR_GREEN="
set "COLOR_YELLOW="
set "COLOR_RED="
set "COLOR_RESET="

REM ================================================================
REM Header
REM ================================================================
echo %COLOR_CYAN%===============================================%COLOR_RESET%
echo %COLOR_CYAN%  Style Engine - Advanced Addon Packaging%COLOR_RESET%
echo %COLOR_CYAN%===============================================%COLOR_RESET%
echo.

REM Initialize log
echo [%date% %time%] Packaging started > "%LOG_FILE%"

REM ================================================================
REM Validation
REM ================================================================
echo Validating environment...

REM Check source directory
if not exist "%SOURCE_DIR%" (
    echo %COLOR_RED%ERROR: Source directory not found: %SOURCE_DIR%%COLOR_RESET%
    echo [ERROR] Source directory not found >> "%LOG_FILE%"
    exit /b 1
)
echo   [+] Source directory found

REM Check config file
if not exist "%CONFIG_FILE%" (
    echo %COLOR_YELLOW%WARNING: Config file not found, using default file list%COLOR_RESET%
    set "USE_CONFIG=0"
) else (
    echo   [+] Config file found
    set "USE_CONFIG=1"
)

REM Check PowerShell availability
powershell -Command "exit 0" >nul 2>&1
if !errorlevel! neq 0 (
    echo %COLOR_RED%ERROR: PowerShell not available%COLOR_RESET%
    echo [ERROR] PowerShell not available >> "%LOG_FILE%"
    exit /b 1
)
echo   [+] PowerShell available

REM Check __init__.py exists and has bl_info
findstr /C:"bl_info" "%SOURCE_DIR%\__init__.py" >nul 2>&1
if !errorlevel! neq 0 (
    echo %COLOR_RED%ERROR: __init__.py missing or invalid (no bl_info)%COLOR_RESET%
    echo [ERROR] Invalid __init__.py >> "%LOG_FILE%"
    exit /b 1
)
echo   [+] Addon metadata valid

echo.

REM ================================================================
REM Cleanup
REM ================================================================
REM Remove old ZIP
if exist "%OUTPUT_ZIP%" (
    echo Removing old ZIP file...
    del /f /q "%OUTPUT_ZIP%" 2>>"%LOG_FILE%"
    if !errorlevel! neq 0 (
        echo %COLOR_RED%ERROR: Could not delete old ZIP%COLOR_RESET%
        exit /b 1
    )
)

REM Clean up old temp directories
for /d %%D in ("%TEMP%\styleengine_package_*") do (
    rd /s /q "%%D" 2>nul
)

echo Creating temporary directory structure...

REM ================================================================
REM Create Package Structure
REM ================================================================
if exist "%TEMP_BASE%" rd /s /q "%TEMP_BASE%" 2>nul
mkdir "%TEMP_BASE%" 2>>"%LOG_FILE%"
mkdir "%TEMP_ADDON%" 2>>"%LOG_FILE%"

if !errorlevel! neq 0 (
    echo %COLOR_RED%ERROR: Could not create temp directory%COLOR_RESET%
    exit /b 1
)
echo   [+] Temp directory created: %TEMP_ADDON%
echo.

REM ================================================================
REM Copy Files
REM ================================================================
echo %COLOR_CYAN%Packaging files...%COLOR_RESET%
echo.

set "FILE_COUNT=0"
set "ERROR_COUNT=0"

if "%USE_CONFIG%"=="1" (
    REM Use config file
    for /f "usebackq tokens=* delims=" %%L in ("%CONFIG_FILE%") do (
        set "LINE=%%L"
        REM Skip comments and empty lines
        if not "!LINE:~0,1!"=="#" if not "!LINE!"=="" (
            if exist "%SOURCE_DIR%\!LINE!" (
                REM Create subdirectories if needed
                for %%F in ("!LINE!") do set "FILE_DIR=%%~dpF"
                if not "!FILE_DIR!"=="\" (
                    if not exist "%TEMP_ADDON%\!FILE_DIR!" mkdir "%TEMP_ADDON%\!FILE_DIR!" 2>nul
                )
                
                copy /y "%SOURCE_DIR%\!LINE!" "%TEMP_ADDON%\!LINE!" >nul 2>&1
                if !errorlevel! equ 0 (
                    echo   %COLOR_GREEN%[+]%COLOR_RESET% !LINE!
                    set /a FILE_COUNT+=1
                ) else (
                    echo   %COLOR_RED%[!]%COLOR_RESET% Failed to copy !LINE!
                    echo [ERROR] Failed to copy !LINE! >> "%LOG_FILE%"
                    set /a ERROR_COUNT+=1
                )
            ) else (
                echo   %COLOR_YELLOW%[!]%COLOR_RESET% !LINE! ^(not found, skipping^)
                echo [WARNING] File not found: !LINE! >> "%LOG_FILE%"
            )
        )
    )
) else (
    REM Use default file list
    set FILES=__init__.py prefs.py ui_panel.py workspace_setup.py utils.py runcomfy_client.py runcomfy_deployment.py runcomfy_polling.py README.md
    
    for %%F in (!FILES!) do (
        if exist "%SOURCE_DIR%\%%F" (
            copy /y "%SOURCE_DIR%\%%F" "%TEMP_ADDON%\%%F" >nul 2>&1
            if !errorlevel! equ 0 (
                echo   %COLOR_GREEN%[+]%COLOR_RESET% %%F
                set /a FILE_COUNT+=1
            ) else (
                echo   %COLOR_RED%[!]%COLOR_RESET% Failed to copy %%F
                set /a ERROR_COUNT+=1
            )
        ) else (
            echo   %COLOR_YELLOW%[!]%COLOR_RESET% %%F ^(not found, skipping^)
        )
    )
)

echo.
echo %COLOR_CYAN%Files packaged: %FILE_COUNT%%COLOR_RESET%
if %ERROR_COUNT% gtr 0 (
    echo %COLOR_YELLOW%Errors encountered: %ERROR_COUNT%%COLOR_RESET%
)
echo.

echo Excluded patterns:
echo   %COLOR_YELLOW%[-]%COLOR_RESET% __pycache__/
echo   %COLOR_YELLOW%[-]%COLOR_RESET% *.pyc files
echo   %COLOR_YELLOW%[-]%COLOR_RESET% .git/
echo   %COLOR_YELLOW%[-]%COLOR_RESET% *.zip files
echo   %COLOR_YELLOW%[-]%COLOR_RESET% .DS_Store
echo   %COLOR_YELLOW%[-]%COLOR_RESET% Thumbs.db
echo.

REM ================================================================
REM Validate Package
REM ================================================================
echo Validating package structure...

REM Check critical files
set "VALIDATION_OK=1"

if not exist "%TEMP_ADDON%\__init__.py" (
    echo   %COLOR_RED%[!] CRITICAL: __init__.py missing%COLOR_RESET%
    set "VALIDATION_OK=0"
)

if not exist "%TEMP_ADDON%\prefs.py" (
    echo   %COLOR_RED%[!] CRITICAL: prefs.py missing%COLOR_RESET%
    set "VALIDATION_OK=0"
)

if not exist "%TEMP_ADDON%\ui_panel.py" (
    echo   %COLOR_RED%[!] CRITICAL: ui_panel.py missing%COLOR_RESET%
    set "VALIDATION_OK=0"
)

if "%VALIDATION_OK%"=="0" (
    echo.
    echo %COLOR_RED%ERROR: Package validation failed%COLOR_RESET%
    echo [ERROR] Package validation failed >> "%LOG_FILE%"
    rd /s /q "%TEMP_BASE%"
    exit /b 1
)

echo   %COLOR_GREEN%[+] Package structure valid%COLOR_RESET%
echo.

REM ================================================================
REM Create ZIP Archive
REM ================================================================
echo Creating ZIP archive...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; try { Add-Type -Assembly System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::CreateFromDirectory('%TEMP_ADDON%', '%OUTPUT_ZIP%', [System.IO.Compression.CompressionLevel]::Optimal, $false); exit 0 } catch { Write-Host 'ERROR: ' $_.Exception.Message; exit 1 }" 2>>"%LOG_FILE%"

if !errorlevel! neq 0 (
    echo %COLOR_RED%ERROR: Failed to create ZIP archive%COLOR_RESET%
    echo [ERROR] ZIP creation failed >> "%LOG_FILE%"
    rd /s /q "%TEMP_BASE%"
    exit /b 1
)

REM Clean up temp directory
rd /s /q "%TEMP_BASE%" 2>nul

REM ================================================================
REM Verify and Report
REM ================================================================
if exist "%OUTPUT_ZIP%" (
    REM Get ZIP size
    for %%A in ("%OUTPUT_ZIP%") do set "ZIP_SIZE=%%~zA"
    set /a ZIP_SIZE_KB=!ZIP_SIZE! / 1024
    
    REM Verify ZIP integrity
    powershell -NoProfile -Command "Add-Type -Assembly System.IO.Compression.FileSystem; try { $zip = [System.IO.Compression.ZipFile]::OpenRead('%OUTPUT_ZIP%'); $count = $zip.Entries.Count; $zip.Dispose(); Write-Host $count; exit 0 } catch { exit 1 }" > "%TEMP%\zip_count.txt" 2>nul
    
    set /p ZIP_ENTRY_COUNT=<"%TEMP%\zip_count.txt"
    del "%TEMP%\zip_count.txt" 2>nul
    
    echo %COLOR_CYAN%===============================================%COLOR_RESET%
    echo %COLOR_GREEN%  SUCCESS!%COLOR_RESET%
    echo %COLOR_CYAN%===============================================%COLOR_RESET%
    echo.
    echo Package: %OUTPUT_ZIP%
    echo Size: !ZIP_SIZE_KB! KB
    echo Files: !ZIP_ENTRY_COUNT!
    echo Platform: Cross-compatible (Windows/macOS/Linux)
    echo.
    echo %COLOR_CYAN%Installation Instructions:%COLOR_RESET%
    echo 1. Open Blender 4.2+
    echo 2. Edit -^> Preferences -^> Add-ons
    echo 3. Click "Install from Disk..."
    echo 4. Select: %OUTPUT_ZIP%
    echo 5. Enable "Style Engine" checkbox
    echo 6. Configure RunComfy API credentials
    echo.
    echo %COLOR_GREEN%Log file: %LOG_FILE%%COLOR_RESET%
    echo.
    
    echo [SUCCESS] Package created: !ZIP_SIZE_KB! KB, !ZIP_ENTRY_COUNT! files >> "%LOG_FILE%"
) else (
    echo %COLOR_RED%===============================================%COLOR_RESET%
    echo %COLOR_RED%  FAILED!%COLOR_RESET%
    echo %COLOR_RED%===============================================%COLOR_RESET%
    echo.
    echo ERROR: ZIP package was not created
    echo Check log file: %LOG_FILE%
    echo.
    echo [ERROR] Final verification failed >> "%LOG_FILE%"
    exit /b 1
)

endlocal
exit /b 0

