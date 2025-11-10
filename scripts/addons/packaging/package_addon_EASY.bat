@echo off
REM ================================================================
REM    Style Engine - Easy Packaging Script
REM    Simple wrapper that runs the modern Python packaging script
REM ================================================================

echo.
echo ================================================================
echo   Style Engine - Addon Packaging
echo ================================================================
echo.

REM Try to find Python
where python >nul 2>nul
if %errorlevel% equ 0 (
    echo Found: python
    python "%~dp0package_addon_modern.py"
    goto :done
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    echo Found: py
    py "%~dp0package_addon_modern.py"
    goto :done
)

where python3 >nul 2>nul
if %errorlevel% equ 0 (
    echo Found: python3
    python3 "%~dp0package_addon_modern.py"
    goto :done
)

REM Python not found
echo.
echo ERROR: Python not found!
echo.
echo Please install Python 3.7 or newer:
echo   https://www.python.org/downloads/
echo.
echo Or run the Python script directly:
echo   python package_addon_modern.py
echo.
pause
exit /b 1

:done
echo.
if %errorlevel% equ 0 (
    echo ================================================================
    echo   SUCCESS! Package created.
    echo ================================================================
) else (
    echo ================================================================
    echo   ERROR: Packaging failed.
    echo ================================================================
)
echo.
pause
exit /b %errorlevel%

