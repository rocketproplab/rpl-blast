# PowerShell script to install a local Python + env using micromamba (no global changes)
# and install project requirements into it.

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$MambaRoot = Join-Path $Root ".mamba"
$EnvPrefix = Join-Path $Root ".venv"
$Micromamba = Join-Path $MambaRoot "micromamba.exe"

Write-Host "Project root: $Root"

if (!(Test-Path $Micromamba)) {
    Write-Host "Downloading micromamba..."
    New-Item -ItemType Directory -Force -Path $MambaRoot | Out-Null
    $url = "https://micro.mamba.pm/api/micromamba/win-64/latest"
    $tmp = Join-Path $MambaRoot "micromamba.tar.bz2"
    Invoke-WebRequest -Uri $url -OutFile $tmp
    try {
        tar -xvjf $tmp -C $MambaRoot "Library/bin/micromamba.exe" 2>$null
        if (Test-Path (Join-Path $MambaRoot "Library/bin/micromamba.exe")) {
            Move-Item -Force (Join-Path $MambaRoot "Library/bin/micromamba.exe") $Micromamba
        } else {
            tar -xvjf $tmp -C $MambaRoot "bin/micromamba.exe" 2>$null
            if (Test-Path (Join-Path $MambaRoot "bin/micromamba.exe")) {
                Move-Item -Force (Join-Path $MambaRoot "bin/micromamba.exe") $Micromamba
            } else {
                throw "Failed to extract micromamba.exe"
            }
        }
    } finally {
        if (Test-Path $tmp) { Remove-Item $tmp -Force }
    }
}

$env:MAMBA_ROOT_PREFIX = $MambaRoot
if (!(Test-Path $EnvPrefix)) {
    Write-Host "Creating local env at $EnvPrefix..."
    & $Micromamba create -y -p $EnvPrefix "python=3.9" pip
}

Write-Host "Installing Python packages into local env..."
& $Micromamba run -p $EnvPrefix python -m pip install -r (Join-Path $Root "requirements.txt")

Write-Host "Setup complete. To start the app:"
Write-Host "  PowerShell -ExecutionPolicy Bypass -File scripts\start_win.ps1"

