@echo off
cd /d "%~dp0"
python migrate_previous.py
python main.py
pause
