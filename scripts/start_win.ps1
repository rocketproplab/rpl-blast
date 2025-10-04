$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$MambaRoot = Join-Path $Root ".mamba"
$EnvPrefix = Join-Path $Root ".venv"
$Micromamba = Join-Path $MambaRoot "micromamba.exe"

if (!(Test-Path $Micromamba)) { throw "micromamba not found. Run scripts\setup_win.ps1 first." }
$env:MAMBA_ROOT_PREFIX = $MambaRoot

$HostName = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$PortNum = if ($env:PORT) { $env:PORT } else { "8000" }
Write-Host ("Starting BLAST FastAPI at http://{0}:{1} ..." -f $HostName, $PortNum)
& $Micromamba run -p $EnvPrefix uvicorn backend.app.main:app --host $HostName --port $PortNum
