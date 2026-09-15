@echo off
rem Workspace bootstrap entry (Windows); calls setup_workspace.py
rem Note: symlinks require Developer Mode or Administrator; Linux is preferred for doc work.
setlocal
set "SCRIPT_DIR=%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo python not found in PATH. Install Python 3 first.
  exit /b 1
)

python "%SCRIPT_DIR%setup_workspace.py" %*
exit /b %errorlevel%
