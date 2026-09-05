@echo off
setlocal
if "%~1"=="" (
  echo Usage: autofill_rehearsal.bat APPLICATION_URL
  exit /b 1
)
python autofill_rehearsal.py "%~1"
