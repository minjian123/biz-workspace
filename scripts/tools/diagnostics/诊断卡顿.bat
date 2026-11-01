@echo off
rem Stuck diagnosis entry (Windows); calls diagnose_stuck.py
rem No args = two samples 3s apart; --interval / --rounds / --busy-mbps / --stale-seconds / --json
setlocal
set "SCRIPT_DIR=%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo python not found in PATH. Install Python 3 first.
  exit /b 2
)

python "%SCRIPT_DIR%diagnose_stuck.py" %*
exit /b %errorlevel%
