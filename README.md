# Driver Monitor Prototype

This is a simple webcam-based driver monitoring system. It uses MediaPipe Face Mesh to track facial landmarks and OpenCV to show a live video window with colored status messages.

## What it shows

- Red: `WARNING: EYES CLOSED`
- Green: `EYE'S OPEN`
- Yellow: `LOOKING DOWN`
- Pink: `TONGUE OUT`
- Mint: `SMILING`
- Blue/orange: `MOUTH OPEN`
- Purple: `PUCKERING`

Closed eyes and looking down take priority over expressions so safety warnings remain visible when multiple detections happen at once.

## Setup

Open PowerShell in this folder:

```powershell
cd C:\Users\chees\Documents\Codex\2026-06-24\how-can-i-make-a-driver\outputs\driver_monitor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python driver_monitor.py
```

Press `Q` to close the camera window.

## Build the Windows app

```powershell
.\build_exe.ps1
```

After the build finishes, run:

```powershell
.\dist\DriverMonitor\DriverMonitor.exe
```

## Install like a normal app

Run PowerShell in this folder:

```powershell
.\install_driver_monitor.ps1
```

This copies the app to:

```text
%LOCALAPPDATA%\DriverMonitor
```

It also creates:

- a Desktop shortcut named `Driver Monitor`
- a Start Menu shortcut named `Driver Monitor`

To remove it later:

```powershell
.\uninstall_driver_monitor.ps1
```

## Tuning

If detection feels too sensitive or not sensitive enough, run:

```powershell
python driver_monitor.py --debug
```

Useful settings:

```powershell
python driver_monitor.py --eye-closed-threshold 0.19 --look-down-threshold 16 --smile-threshold 0.5
```

Try increasing `--look-down-threshold` if it says looking down too often. Try lowering `--eye-closed-threshold` if it says eyes are closed while they are open.
Tongue detection is approximate because the model does not directly label the tongue; try increasing `--tongue-color-threshold` if it triggers too easily.

## Note

This is a learning prototype, not a safety-certified automotive system. Real driver monitoring needs infrared cameras, low-light testing, fail-safe behavior, and extensive validation.
