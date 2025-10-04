@echo off
setlocal
set SCRIPT_DIR=%~dp0
PowerShell -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%uninstall_win.ps1"
endlocal

