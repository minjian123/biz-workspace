@echo off
rem Workspace hygiene check entry (Windows); calls check_workspace_hygiene.py
rem No args = check (exit 1 on violation); --clean = quarantine into tmp/_quarantine/
setlocal
set "SCRIPT_DIR=%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo python not found in PATH. Install Python 3 first.
  exit /b 2
)

python "%SCRIPT_DIR%check_workspace_hygiene.py" %*
exit /b %errorlevel%
