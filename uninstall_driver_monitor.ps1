$ErrorActionPreference = "Stop"

$InstallDir = Join-Path $env:LOCALAPPDATA "DriverMonitor"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "Driver Monitor.lnk"
$StartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "Driver Monitor"

Get-Process DriverMonitor -ErrorAction SilentlyContinue | Stop-Process -Force

if (Test-Path $DesktopShortcut) {
    Remove-Item -Force $DesktopShortcut
}

if (Test-Path $StartMenuDir) {
    Remove-Item -Recurse -Force $StartMenuDir
}

if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
}

Write-Host "Driver Monitor uninstalled."
