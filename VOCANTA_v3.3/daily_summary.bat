@echo off
cd /d "%~dp0"
python daily_summary.py
if exist "exports\daily_summary.html" start "" "exports\daily_summary.html"
pause
