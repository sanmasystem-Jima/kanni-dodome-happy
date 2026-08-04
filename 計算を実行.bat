@echo off
cd /d "%~dp0"
python 00_Dodome_Tougou.py
if errorlevel 1 (
    echo.
    echo Calculation stopped. See message above.
    pause
    exit /b 1
)
