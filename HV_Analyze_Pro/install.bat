@echo off
setlocal enabledelayedexpansion

echo ========================================
echo    HVSR Pro - Installation Script
echo ========================================
echo.

REM Change to the directory containing this script
cd /d "%~dp0"

echo [1/5] Checking for Python installation...
echo.

REM Try to find Python on the system
set PYTHON_CMD=

REM Try 'py -3' first (Windows Python Launcher - most reliable)
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_CMD=py -3
    goto :python_found
)

REM Try 'python'
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_CMD=python
    goto :python_found
)

REM Try 'python3'
python3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_CMD=python3
    goto :python_found
)

echo ========================================
echo  ERROR: Python is not installed!
echo ========================================
echo.
echo Please install Python 3.12 from:
echo   https://www.python.org/downloads/
echo.
echo IMPORTANT: During installation, make sure
echo to check "Add Python to PATH"
echo.
pause
exit /b 1

:python_found
echo Found Python:
%PYTHON_CMD% --version
echo.

REM Verify Python version is 3.8+
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>nul
if !errorlevel! neq 0 (
    echo ========================================
    echo  ERROR: Python 3.8 or higher is required
    echo ========================================
    echo.
    echo Please install Python 3.12 from:
    echo   https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [2/5] Creating virtual environment...
echo.

REM Remove old venv if it exists (clean install)
if exist ".venv" (
    echo Removing old virtual environment...
    echo Please close any terminals or apps using this venv.
    echo.

    REM Try to delete - may fail if DLLs are locked
    rmdir /s /q ".venv" 2>nul

    REM Give Windows time to release file locks
    timeout /t 3 /nobreak >nul 2>&1

    REM Check if still there
    if exist ".venv" (
        echo Old .venv could not be fully removed.
        echo Trying again...
        rmdir /s /q ".venv" 2>nul
        timeout /t 2 /nobreak >nul 2>&1
    )

    REM If STILL there, try renaming it out of the way
    if exist ".venv" (
        echo Renaming old folder out of the way...
        ren ".venv" ".venv_old_%RANDOM%" 2>nul
    )

    REM Final check
    if exist ".venv" (
        echo.
        echo ========================================
        echo  ERROR: Cannot remove old .venv folder
        echo ========================================
        echo.
        echo Some files are locked by Windows.
        echo.
        echo Please do the following:
        echo   1. Close ALL terminals and command prompts
        echo   2. Close any Python applications
        echo   3. Restart your computer
        echo   4. Manually delete the .venv folder
        echo   5. Run install.bat again
        echo.
        pause
        exit /b 1
    )
)

%PYTHON_CMD% -m venv .venv

if not exist ".venv\Scripts\python.exe" (
    echo ========================================
    echo  ERROR: Failed to create virtual environment
    echo ========================================
    echo.
    echo Try reinstalling Python with default options.
    echo.
    pause
    exit /b 1
)

echo Virtual environment created successfully.
echo.

echo [3/5] Upgrading pip...
echo.
.venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
echo Pip upgraded.
echo.

echo [4/5] Installing dependencies from requirements.txt...
echo      This may take a few minutes...
echo.
.venv\Scripts\python.exe -m pip install -r requirements.txt

if !errorlevel! neq 0 (
    echo.
    echo ========================================
    echo  ERROR: Package installation failed
    echo ========================================
    echo.
    echo Some packages failed to install.
    echo Please check the error messages above.
    echo.
    echo Common fixes:
    echo   - Make sure you have internet access
    echo   - Try running this script as Administrator
    echo   - Close all terminals, delete .venv folder,
    echo     and run install.bat again
    echo.
    pause
    exit /b 1
)

echo.
echo [5/5] Verifying installation...
echo.

REM Test that all critical imports work
.venv\Scripts\python.exe -c "import numpy; import scipy; import matplotlib; import PyQt5; import obspy; print('  numpy      ' + numpy.__version__); print('  scipy      ' + scipy.__version__); print('  matplotlib ' + matplotlib.__version__); print('  obspy      ' + obspy.__version__); print(); print('All packages verified successfully!')"

if !errorlevel! neq 0 (
    echo.
    echo ========================================
    echo  WARNING: Import verification failed
    echo ========================================
    echo.
    echo Packages installed but some imports failed.
    echo Try deleting .venv and running install.bat again.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Installation Complete!
echo ========================================
echo.
echo To run HVSR Pro, double-click: launch.bat
echo.
echo ========================================
pause

