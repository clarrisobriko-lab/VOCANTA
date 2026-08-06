@echo off
setlocal
cd /d "%~dp0"
python doctor.py
set RESULT=%ERRORLEVEL%
pause
exit /b %RESULT%
