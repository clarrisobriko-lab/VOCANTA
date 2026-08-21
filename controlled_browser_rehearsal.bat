@echo off
cd /d "%~dp0"
python controlled_browser_rehearsal.py
if errorlevel 1 echo Controlled browser rehearsal stopped safely.
pause
