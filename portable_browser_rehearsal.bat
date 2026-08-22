@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: portable_browser_rehearsal.bat JOB_ID
  exit /b 2
)
python portable_browser_rehearsal.py %1
if errorlevel 1 echo Portable browser rehearsal stopped safely.
pause
