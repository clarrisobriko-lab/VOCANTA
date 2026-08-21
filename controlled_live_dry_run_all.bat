@echo off
cd /d "%~dp0"
python controlled_live_intake.py
if errorlevel 1 goto :error
python controlled_live_dry_run.py
if errorlevel 1 goto :error
echo.
echo Controlled live dry run completed safely.
goto :done
:error
echo.
echo Controlled live dry run stopped safely because a prerequisite failed.
:done
pause
