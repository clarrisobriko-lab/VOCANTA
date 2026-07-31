@echo off
setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Install Python 3.12 or newer and select Add Python to PATH.
  exit /b 1
)

python -c "import pytest" >nul 2>&1
if errorlevel 1 (
  echo Installing VOCANTA verification tools...
  python -m pip install -r requirements-test.txt
  if errorlevel 1 (
    echo.
    echo VOCANTA could not install its verification tools.
    exit /b 1
  )
)

python -m pytest -q tests
if errorlevel 1 (
  echo.
  echo VOCANTA tests failed.
  exit /b 1
)

echo.
echo VOCANTA tests passed.
endlocal
exit /b 0
