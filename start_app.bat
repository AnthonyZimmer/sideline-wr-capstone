@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run: creating a Python 3.12 environment.
  py -3.12 -m venv .venv
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
start "" http://127.0.0.1:5000
".venv\Scripts\python.exe" app.py
goto :eof
:fail
echo Setup failed. Read README.md for the manual setup commands.
pause
