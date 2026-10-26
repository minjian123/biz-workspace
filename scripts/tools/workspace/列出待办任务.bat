@echo off
rem Workspace plan overview entry (Windows); calls list_pending_tasks.py
rem No args = list all pending tasks (sorted by schedule window); see the script docstring for flags
setlocal
set "SCRIPT_DIR=%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo python not found in PATH. Install Python 3 first.
  exit /b 2
)

python "%SCRIPT_DIR%list_pending_tasks.py" %*
exit /b %errorlevel%
