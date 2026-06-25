$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $ProjectDir ".venv")
}

Push-Location $ProjectDir
& $Python -m pip install -r (Join-Path $ProjectDir "requirements.txt")
& $Python -m PyInstaller --clean --noconfirm "driver_monitor.spec"
Pop-Location

Write-Host ""
Write-Host "Built app:"
Write-Host (Join-Path $ProjectDir "dist\DriverMonitor\DriverMonitor.exe")
