# EEG Analyse

`EEG Analyse` is now a local web-based application for Muse EEG/PPG acquisition, live signal visualization, recording, and Focus Game experiment sessions.

## Main Features

- Browser-based Analyse dashboard
- Muse device scan, connect, disconnect, and battery check
- Live EEG and PPG canvas plots
- Manual EEG/PPG recording to CSV
- Browser-based Focus Game with Relax, Break, and Game stages
- Guided N-back demo mode
- Participant metadata, session planner, consent capture, and result export
- Master control workbook updates for game results

## Project Structure

```text
EEG/
├── WEB_APP/             # Local web server and browser UI
│   └── static/          # HTML, CSS, and JavaScript frontend
├── EEG_APP/             # Device, streaming, processing, storage
├── GAME/                # Game rules, participant task data, result helpers
│   └── n_back/          # Focus Game configuration and persistence helpers
├── UI/                  # Legacy PyQt desktop UI kept for fallback only
├── main.py              # Web app entry point
└── desktop_main.py      # Legacy desktop entry point
```

## Requirements

- Python 3.12 or newer
- Muse headset
- `muselsl`
- `mne-lsl`
- `numpy`
- `scipy`

The web runtime uses Python's standard HTTP server, so no separate web framework is required.

## Setup

Create a fresh virtual environment from the project root:

```bash
chmod +x setup_venv.sh
./setup_venv.sh
source .venv/bin/activate
```

## Run The Web App

From the project root:

```bash
python main.py
```

By default the app runs at:

```text
http://127.0.0.1:8000
```

Useful options:

```bash
python main.py --host 127.0.0.1 --port 8000
python main.py --no-browser
```

## Workflow

### Analyse

1. Open the web app in your browser.
2. Use `Scan Devices` to find nearby Muse headsets.
3. Select a Muse device and click `Connect`.
4. Watch the live EEG/PPG plots and metrics.
5. Use `Record Data` and `Stop Recording` for manual CSV capture.

### Experiment Set-Up

1. Fill participant fields: `Name`, `ID`, `DeviceID`, `Age`, `N Value`, and `Note`.
2. Configure Relax, Break, and Game order and duration.
3. Choose the game language and relax music track.
4. Use `Play Demo` for guided N-back practice.
5. Use `Start Game` to run the full browser-based session.

## Focus Game

The Focus Game is an N-back task. The participant must remember the newest `N` letters and press `SPACE` only when the current letter matches the one from `N` steps earlier.

Example for `N = 3`:

- `A, K, D, A` -> press `SPACE` on the last `A`
- `A, K, D, C` -> do not press

When the game starts, the browser asks for consent, then runs the planned Relax, Break, and Game stages. If a Muse stream is connected, recording starts automatically at session start and stops automatically at session end.

## Output Files

- EEG/PPG recordings: `EEG_APP/results/`
- Game result CSV: `GAME/n_back/result/`
- Master control workbook: `GAME/n_back/result/Master_Control.xlsx`

## Legacy Desktop Fallback

The old PyQt/Tkinter desktop shell is no longer the default app, but it is still available for comparison:

```bash
python desktop_main.py
```

That fallback still requires the desktop-only dependencies from the older application.

## License and Citation

This software is provided for research and academic use.

If you use this software, you must cite the author in your publication, report, thesis, or project documentation.

Recommended citation:

`Pham, M. C. EEG Analyse Software (Muse EEG/PPG acquisition and Focus Game), RPTU Kaiserslautern-Landau.`

## Author

Manh Cuong Pham  
pmcuong1996@icloud.com  
PhD Candidate at RPTU Kaiserslautern-Landau

