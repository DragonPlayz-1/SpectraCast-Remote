@echo off
setlocal
cd /d "%~dp0.."

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.10+ is required. Install it from https://www.python.org/downloads/
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" python -m venv .venv
.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.venv\Scripts\python.exe -m pip install --quiet -e .
.venv\Scripts\python.exe -m spectracast --lan %*
