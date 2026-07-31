@echo off
cd /d "%~dp0"
if not exist "exports\applications.html" (echo Update at least one job first.&pause&exit /b 1)
start "" "exports\applications.html"
