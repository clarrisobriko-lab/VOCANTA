@echo off
cd /d "%~dp0"
if not exist "exports\shortlisted.html" (echo Run run.bat first.&pause&exit /b 1)
start "" "exports\shortlisted.html"
