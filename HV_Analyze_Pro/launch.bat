@echo off
echo ========================================
echo    HVSR Pro - HVSR Analysis Software
echo ========================================
echo.

REM Change to the directory containing this script
cd /d "%~dp0"

REM Check if the local virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo.
    echo Please run install.bat first to set up the environment.
    echo.
    pause
    exit /b 1
)

echo Starting HVSR Pro...
echo Working directory: %CD%
echo Using Python: %CD%\.venv\Scripts\python.exe
echo.

REM Run the GUI launcher using the local venv Python
.venv\Scripts\python.exe -X faulthandler launch_gui.py

echo.
echo ========================================
echo    Application closed
echo ========================================
pause
