@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0packaging\publish-github.ps1"
if errorlevel 1 (
  echo Publishing failed. Read the error above; no force push is performed.
)
pause
