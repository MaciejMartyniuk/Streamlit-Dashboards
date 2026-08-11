@echo off
setlocal
cd /d "%~dp0"

echo Global Supply Chain Monitor
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python not found. Install it from https://www.python.org/downloads/
    echo During setup, check "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

if errorlevel 1 (
    echo.
    echo Failed to install dependencies. Try manually:
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo Starting dashboard...
echo (To stop, return to this window and press CTRL+C)
echo.

python -m streamlit run app.py

pause
