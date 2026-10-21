@echo off
cd /d "%~dp0"
python app.py
if errorlevel 1 (
    echo.
    echo ===================================================
    echo [Antigravity Skill Studio] 启动失败
    echo 请确认已安装 Python 并安装了项目依赖:
    echo     pip install -r requirements.txt
    echo ===================================================
    echo.
    pause
)
