@echo off
cd /d "%~dp0"
python retry_email_outbox.py
pause
