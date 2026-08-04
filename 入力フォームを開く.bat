@echo off
cd /d "%~dp0"
python tools\01_Dodome_Input_GUI.py
if errorlevel 1 (
    echo.
    echo Failed to launch GUI. See message above.
    pause
)
