@echo off
cd /d "%~dp0"
if errorlevel 1 exit /b 1
"%~dp0.venv\Scripts\python.exe" -X utf8 "%~dp0dev_previews\run_current_app.py" --port 18821
pause
