$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceDir = Join-Path $ProjectDir "dist\DriverMonitor"
$SourceExe = Join-Path $SourceDir "DriverMonitor.exe"
$InstallDir = Join-Path $env:LOCALAPPDATA "DriverMonitor"
$InstallExe = Join-Path $InstallDir "DriverMonitor.exe"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "Driver Monitor.lnk"
$StartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "Driver Monitor"
$StartMenuShortcut = Join-Path $StartMenuDir "Driver Monitor.lnk"

if (-not (Test-Path $SourceExe)) {
    throw "DriverMonitor.exe was not found at $SourceExe. Build the app first."
}

if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $SourceDir "*") $InstallDir

New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null

$Shell = New-Object -ComObject WScript.Shell

$Desktop = $Shell.CreateShortcut($DesktopShortcut)
$Desktop.TargetPath = $InstallExe
$Desktop.WorkingDirectory = $InstallDir
$Desktop.Description = "Driver Monitor"
$Desktop.Save()

$StartMenu = $Shell.CreateShortcut($StartMenuShortcut)
$StartMenu.TargetPath = $InstallExe
$StartMenu.WorkingDirectory = $InstallDir
$StartMenu.Description = "Driver Monitor"
$StartMenu.Save()

Write-Host "Driver Monitor installed."
Write-Host "Installed to: $InstallDir"
Write-Host "Desktop shortcut: $DesktopShortcut"
Write-Host "Start menu shortcut: $StartMenuShortcut"
