@echo off
echo ========================================
echo    HVSR Pro - HVSR Analysis Software
echo ========================================
echo.

REM Change to the directory containing this script
cd /d "%~dp0"

echo Starting HVSR Pro...
echo Working directory: %CD%
echo.

REM Run the GUI launcher
python launch_gui.py

echo.
echo ========================================
echo    Application closed
echo ========================================
pause
