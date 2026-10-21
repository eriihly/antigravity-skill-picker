@echo off
cd /d "%~dp0"
python app.py
if errorlevel 1 (
    echo.
    echo ===================================================
    echo Antigravity Skill Studio failed to start.
    echo Please ensure Python and dependencies are installed:
    echo     pip install -r requirements.txt
    echo ===================================================
    echo.
    pause
)
