@echo off
cd /d "%~dp0"
python migrate_previous.py --manual
pause
