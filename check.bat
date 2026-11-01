@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
python main.py --check
set "CHECK_EXIT=%errorlevel%"
echo.
pause
exit /b %CHECK_EXIT%
