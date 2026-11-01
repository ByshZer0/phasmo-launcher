@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"

where pythonw.exe >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw.exe "%~dp0main.py"
    exit /b 0
)

where python.exe >nul 2>nul
if %errorlevel%==0 (
    python.exe "%~dp0main.py"
    exit /b %errorlevel%
)

echo.
echo 未找到 Python。请先安装 Python 3.10 或更高版本，并勾选 "Add Python to PATH"。
echo 下载地址: https://www.python.org/downloads/windows/
echo.
pause
exit /b 1
