@echo off
setlocal
set SCRIPT_DIR=%~dp0
PowerShell -NoExit -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%start_win.ps1"
endlocal
