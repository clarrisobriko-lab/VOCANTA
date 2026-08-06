@echo off
cd /d "%~dp0"
python migrate_previous.py
if errorlevel 1 goto :error
python main.py
if errorlevel 1 goto :error
echo.
choice /C MACBQ /N /M "M manual, A automated, C action centre, B morning brief, Q quit: "
if errorlevel 5 exit /b 0
if errorlevel 4 goto :brief
if errorlevel 3 goto :centre
if errorlevel 2 goto :automated
cls
python application_center.py
goto :done
:automated
cls
python automated_apply.py
goto :done
:error
echo.
echo VOCANTA stopped because a command failed.
:done
pause
