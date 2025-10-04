$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Venv = Join-Path $Root ".venv"
$Mamba = Join-Path $Root ".mamba"

Write-Host "This will remove the local Python environment in:" -ForegroundColor Yellow
Write-Host "  $Venv"
Write-Host "  $Mamba"
$ans = Read-Host "Proceed? (y/N)"
if (-not ($ans -eq 'y' -or $ans -eq 'Y')) { Write-Host "Aborted."; exit 1 }

if (Test-Path $Venv) { Remove-Item -Recurse -Force $Venv }
if (Test-Path $Mamba) { Remove-Item -Recurse -Force $Mamba }
Write-Host "Local environment removed."

