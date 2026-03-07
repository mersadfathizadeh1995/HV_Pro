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
    echo Please run:  python -m venv .venv
    echo Then run:    .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo Starting HVSR Pro...
echo Working directory: %CD%
echo.

REM Run the GUI launcher using the local venv Python
.venv\Scripts\python.exe -X faulthandler launch_gui.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited with error code %ERRORLEVEL%
)
echo.
echo ========================================
echo    Application closed
echo ========================================
pause
