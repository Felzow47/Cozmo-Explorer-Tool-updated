# Cozmo Explorer Tool

A web-based control panel for the Anki Cozmo robot. Drive Cozmo from your keyboard, watch the live camera feed, browse and play built-in animations, and monitor robot events in real time.

This project has been migrated from the official Anki Cozmo SDK to [PyCozmo](https://github.com/zayfod/pycozmo). The robot connects over Wi-Fi directly from your PC - no mobile phone or Cozmo app required.

![Cozmo Explorer Tool](static/img/explorer-tool-v0.5.jpg)

## Overview

Running `explorer_tool.py` starts a local Flask web server and opens a browser at [http://127.0.0.1:5000/](http://127.0.0.1:5000/). The interface is divided into three sections:

1. **Robot camera and control** - Live camera feed with keyboard-driven movement. Hover over the feed to see on-screen control hints. Toggle the IR headlight, enable freeplay mode, or switch the feed to fullscreen.

2. **Event monitor** - Real-time log of robot state changes (picked up, falling, on charger, and more) streamed over Socket.IO.

3. **Animations** - Browse, search, and play Cozmo's built-in animations, triggers, and behaviors. Includes grouping and filtering tools inherited from the original Animation Explorer.

If the robot cannot be reached at startup, the web UI still launches in **demo mode** so you can inspect the interface before connecting.

## Requirements

| Item | Details |
|------|---------|
| Robot | Anki Cozmo (powered on) |
| PC | Windows, macOS, or Linux |
| Python | 3.8 or later (tested with Python 3.14) |
| Network | Wi-Fi adapter to join the Cozmo access point |
| Dependencies | See `requirements.txt` |

You do **not** need:

- The Cozmo mobile app
- A USB cable between phone and PC
- The official Anki Cozmo SDK

## Installation

1. Clone or download this repository.

2. Create a virtual environment (recommended):

   ```bash
   python -m venv .venv
   ```

   Windows:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

   macOS / Linux:

   ```bash
   source .venv/bin/activate
   ```

3. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   Packages installed:

   - `flask` - web server
   - `flask-socketio` - real-time event monitor
   - `Pillow` - camera image processing
   - `pycozmo` - direct robot communication
   - `standard-chunk` - required on Python 3.13+

4. Install the **entire project directory**, not just `explorer_tool.py`. The tool depends on `templates/`, `static/`, and other modules in this repo.

## PyCozmo resources setup

PyCozmo needs Cozmo animation and sound assets extracted from the original app package. These are downloaded once and stored locally (default: `~/pycozmo/assets` on Linux/macOS, `%USERPROFILE%\pycozmo\assets` on Windows).

On the **first launch** of `explorer_tool.py`, if resources are missing, the tool downloads and extracts them automatically (~150 MB). You only need the manual steps below if you prefer to install resources before running the tool, or if the automatic download fails.

### Download resources manually (optional)

After installing `pycozmo`, run the resource manager script from your Python **Scripts** folder. Do **not** use `python -m pycozmo_resources` - that module entry point is not available.

**Windows** (adjust the Python version folder if needed):

```powershell
python "$env:APPDATA\Python\Python314\Scripts\pycozmo_resources.py" download
```

If `Scripts` is on your `PATH`, you can also run:

```powershell
pycozmo_resources.py download
```

**macOS / Linux**:

```bash
python "$(python -m site --user-base)/bin/pycozmo_resources.py" download
```

The download fetches roughly 150 MB from the Cozmo app archive and extracts animations, sounds, and metadata. Run it once per machine.

### Verify resources

```bash
pycozmo_resources.py status
```

Expected output when resources are present:

```
Resources found in C:\Users\<you>\pycozmo\assets
```

If resources are missing and automatic download fails, `explorer_tool.py` prints an error and exits before connecting to the robot.

## Running the tool

From the project root:

```bash
python explorer_tool.py
```

On success you should see:

```
Cozmo connected via PyCozmo. Open http://127.0.0.1:5000/
```

A browser window opens automatically after a short delay. If it does not, navigate to [http://127.0.0.1:5000/](http://127.0.0.1:5000/) manually.

Press `Ctrl+C` in the terminal to stop the server and disconnect from the robot.

### API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Main web UI |
| `GET /health` | Server health check (JSON) |
| `GET /ui-bootstrap` | UI bootstrap data: animation lists, connection status, dependency flags |
| `GET /api/ui-bootstrap` | Alias for `/ui-bootstrap` |

Example health response:

```json
{
  "ok": true,
  "robotConnected": true,
  "animCount": 1234,
  "hasPillow": true,
  "hasSocketIO": true
}
```

## Connecting to Cozmo (Wi-Fi)

1. Power on Cozmo and wait until he is ready (screen shows eyes, not a setup prompt).

2. On your PC, connect to the Cozmo Wi-Fi network. The SSID is usually `Cozmo-XXXX` (last four digits of the serial number).

3. Cozmo acts as a Wi-Fi access point. The robot is typically reachable at `172.31.1.1`.

4. Run `python explorer_tool.py`. PyCozmo waits up to 30 seconds for the robot to appear.

### Windows: Ethernet + Wi-Fi

On Windows you can keep an Ethernet cable plugged in for internet access while using Wi-Fi to talk to Cozmo:

- Connect Wi-Fi to the `Cozmo-XXXX` network.
- Leave Ethernet connected for your normal internet connection.
- Windows routes local traffic to Cozmo over Wi-Fi while Ethernet handles external traffic.

If connection fails, temporarily disable Ethernet or set the Cozmo Wi-Fi connection to a higher priority in Windows network adapter settings.

### Troubleshooting connection

| Symptom | Things to check |
|---------|-----------------|
| `Resources not found` | Re-run `explorer_tool.py` to auto-download, or run `pycozmo_resources.py download` manually |
| `Could not connect to Cozmo` | Cozmo is powered on and not in setup mode |
| Timeout after 30 s | PC is joined to `Cozmo-XXXX` Wi-Fi, not your home network |
| Demo mode in the UI | Restart `explorer_tool.py` after joining Cozmo Wi-Fi |
| Port 5000 already in use | Close any other instance of the tool or change the port in `flask_socket_helpers.py` |
| No camera feed | Confirm `Pillow` is installed (`pip install Pillow`) |
| No event monitor | Confirm `flask-socketio` is installed (`pip install flask-socketio`) |

## Features

- **Live camera feed** with optional pose, accelerometer, and gyro overlay
- **Keyboard remote control** (WASD movement, head and lift controls)
- **QWERTY / AZERTY layout toggle** - click the layout button on the control overlay; preference is saved in the browser
- **On-screen buttons** for movement when using a mouse or touch screen
- **IR headlight toggle**
- **Freeplay mode** - Cozmo roams and reacts autonomously
- **Animation explorer** - search, filter, and play hundreds of built-in animations
- **Triggers and behaviors** - separate tabs for animation groups and behavior activation
- **Event monitor** - Socket.IO stream of robot state changes
- **Demo mode** - UI loads without a robot for inspection and testing

## Keyboard layouts

Controls use **logical** QWERTY key names. Physical key positions are remapped when AZERTY mode is active.

### QWERTY (default)

| Key | Action |
|-----|--------|
| W / S | Drive forward / backward |
| A / D | Turn left / right |
| Q / E | Head up / down |
| R / F | Lift up / down |
| Shift (hold) | Faster movement |
| Alt (hold) | Slower movement |
| Space | Say text (see limitations) |

### AZERTY

Click the **QWERTY** / **AZERTY** toggle on the control overlay. Physical keys are remapped so that the keys in the same positions as W/A/S/D on a QWERTY board control driving:

| Physical key (AZERTY) | Logical action |
|-----------------------|----------------|
| Z | Forward (W) |
| Q | Turn left (A) |
| S | Backward (S) |
| D | Turn right (D) |
| A | Head up (Q) |
| E | Head down (E) |

R, F, Shift, and Alt work the same on both layouts.

## Limitations (PyCozmo vs official SDK)

This tool uses PyCozmo instead of the discontinued Anki SDK. Most Explorer Tool features work, but some SDK capabilities are not available:

| Feature | Status |
|---------|--------|
| Drive, head, lift, camera | Supported |
| Animations, triggers, behaviors | Supported |
| Freeplay mode | Supported via PyCozmo Brain |
| IR headlight | Supported |
| Text-to-speech (`say_text`, Space key) | **Not supported** - logged to console only |
| Official vision events (face, cube, pet detection) | Limited - event monitor reports basic state (picked up, falling, charger) rather than full SDK vision events |
| Mobile app / USB relay | Not required (this is a feature, not a limitation) |

For full vision-event debugging as in the original SDK-based tool, you would need the official SDK with a phone relay. PyCozmo covers the core remote-control and animation-explorer use cases without that setup.

## Project structure

```
explorer_tool.py      # Entry point - starts server and connects to Cozmo
pycozmo_assets.py     # PyCozmo resource check and first-run download
robot_session.py      # PyCozmo session adapter
remote_control.py     # Keyboard and HTTP drive controls
viewer.py             # Camera feed and image annotations
animate.py            # Animation, trigger, and behavior playback
event_monitor.py      # Robot state polling for the event log
flask_socket_helpers.py
templates/            # HTML templates
static/               # CSS, JavaScript, images, fonts
requirements.txt
```

## TO-DO 

Fix : Some keys stay pressed down even though I'm not touching them anymore, so Cozmo moves on his own.
Fix : Try to fix the lagging camera!
Fix : No sound from cozmo
Fix : Get the cubes working again using light and recognition.
Fix : Behaviors because none of them work
Refacto : recreate the web ui from zero.
Feature : Add gamepad support so it's more precise than the keyboard.
Feature : try to Run the mobile app's Scratch code editor on a PC, since it's just a basic web page.

## Credits

- Original tool by [GrinningHermit](https://github.com/GrinningHermit)
- Derived from Anki SDK `remote_control_cozmo.py` and [cozmo-tools](https://github.com/touretzkyds/cozmo-tools) event monitor
- PyCozmo migration for direct Wi-Fi control without the mobile app

## License

MIT License - see [LICENSE](LICENSE).
