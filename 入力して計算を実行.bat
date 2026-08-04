@echo off
cd /d "%~dp0"

echo --- 入力フォームを開きます。保存して閉じると続けて計算を実行します ---
python tools\01_Dodome_Input_GUI.py
if errorlevel 1 (
    echo.
    echo Failed to launch GUI. See message above.
    pause
    exit /b 1
)

echo.
echo --- 続けて計算を実行します ---
python 00_Dodome_Tougou.py
if errorlevel 1 (
    echo.
    echo Calculation stopped. See message above.
    pause
    exit /b 1
)
