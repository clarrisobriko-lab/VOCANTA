@echo off
setlocal
cd /d "%~dp0"

echo.
echo VOCANTA 3.3 Production Installer
echo =================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Install Python 3.12 or newer and select Add Python to PATH.
  pause
  exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)"
if errorlevel 1 (
  echo VOCANTA 3.3 requires Python 3.12 or newer.
  pause
  exit /b 1
)

echo [1/6] Updating pip...
python -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [2/6] Installing VOCANTA runtime dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/6] Installing browser automation support...
python -m playwright install chromium
if errorlevel 1 goto :error

echo [4/6] Repairing and migrating application history...
python repair_history.py
if errorlevel 1 goto :error

echo [5/6] Running production readiness checks...
python doctor.py
if errorlevel 1 goto :error

echo [6/6] Running VOCANTA verification suite...
call test.bat
if errorlevel 1 goto :error

echo.
echo VOCANTA 3.3 installation completed successfully.
echo Your master CV, cover letter and certificate are included.
echo Run start_vocanta.bat to launch VOCANTA.
pause
exit /b 0

:error
echo.
echo VOCANTA installation failed. Review the error above before running it again.
pause
exit /b 1
