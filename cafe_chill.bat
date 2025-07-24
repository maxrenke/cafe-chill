@echo off
:: Batch script to run Lailloken-UI.py as administrator

set "pythonScript=%~dp0cafe_chill.py"

:: Check if the script is running as administrator
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c %~f0' -Verb RunAs"
    exit /b
)

:: Run the Python script
python "%pythonScript%"