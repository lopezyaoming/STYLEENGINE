@echo off
REM ================================================================
REM    Style Engine - Safe Packaging Script
REM    Simple wrapper that calls the Python packaging script
REM ================================================================

echo ===============================================
echo   Style Engine - Safe Addon Packaging
echo ===============================================
echo.

REM Try python command first
where python >nul 2>nul
if %errorlevel% equ 0 (
    python "%~dp0package_addon.py"
    exit /b %errorlevel%
)

REM Try py launcher
where py >nul 2>nul
if %errorlevel% equ 0 (
    py "%~dp0package_addon.py"
    exit /b %errorlevel%
)

REM Python not found
echo ERROR: Python not found in PATH
echo.
echo Please install Python 3.7+ or run the script directly:
echo   python package_addon.py
echo.
exit /b 1

