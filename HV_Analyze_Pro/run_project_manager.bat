@echo on
echo ================================================
echo    HVSR Pro - Project Manager
echo ================================================
echo.

REM Change to the directory containing this script
cd /d "%~dp0"

REM Try local .venv first, then system python
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo Using virtual environment: .venv
) else (
    set PYTHON=python
    echo Using system Python
)

echo Starting HVSR Pro with Project Manager...
echo Working directory: %CD%
echo.

REM Launch the GUI with unbuffered output so all prints/errors appear in real-time
%PYTHON% -u -X faulthandler launch_gui.py 2>&1

if %ERRORLEVEL% neq 0 (
    echo.
    echo ======================================================================
    echo Application exited with error code %ERRORLEVEL%
    echo ======================================================================
)
echo.
echo ================================================
echo    Application closed
echo ================================================
pause
