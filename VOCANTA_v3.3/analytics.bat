@echo off
cd /d "%~dp0"
python analytics.py
if exist "exports\analytics.html" start "" "exports\analytics.html"
pause
