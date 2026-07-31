@echo off
cd /d "%~dp0"
cls
python application_center.py
if errorlevel 1 (
    echo.
    echo Application Center stopped because an error occurred.
)
pause
