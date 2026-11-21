@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_env.ps1"
if errorlevel 1 exit /b %errorlevel%
endlocal
