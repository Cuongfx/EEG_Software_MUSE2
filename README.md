# EEG Analyse

`EEG Analyse` is a desktop software for Muse-based EEG/PPG acquisition, live signal visualization, recording, and set up Game.

## Main Features

- Activate the Muse 2 by pressing the button on the device. The LED should start flashing.
- Start the software and click the Connect button to search for the Muse device.
- Display live EEG and PPG plots
- Record EEG and PPG to CSV
- Launch `Game` with examiner setup
- Save experiment outputs and participant metadata

## Project Structure

```text
EEG/
├── UI/                  # Main desktop UI (PyQt6)
├── EEG_APP/             # Device, streaming, processing, storage
├── GAME/                # Game registry and game modules
│   └── n_back/          # Focus Game implementation
├── Archieve/            # Legacy/old scripts
└── main.py              # App entry point
```

## Requirements

- Python 3.12 (recommended)
- Muse headset
- `muselsl`
- PyQt6
- Tkinter (for game window)

## Setup

Create a fresh virtual environment from the project root:

```bash
chmod +x setup_venv.sh
./setup_venv.sh
source .venv/bin/activate
```

The script recreates `.venv`, upgrades `pip`, installs the desktop app dependencies from `requirements.txt`, and runs a quick import smoke test.

If you still see a Qt platform plugin error on macOS, clear any inherited Qt variables before launching:

```bash
unset QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QT_QPA_PLATFORM
```

## Run

From project root:

```bash
.venv/bin/python main.py
```

## UI Overview

### Analyse Tab

The Analyse tab is for real-time monitoring and recording.

![Analyse UI](./Analyse.png)

How to use:

1. Click `Connect to Device`
2. Select your Muse headset
3. Wait for stream connection
4. Monitor live EEG/PPG plots
5. Click `Record Data` to start recording
6. Click `Stop Recording` to save

### Experiment Set-Up Tab

The Experiment Set-Up tab is for game launch and examiner configuration.

![Experiment Set-Up UI](./Experiment_Set_up.png)

How to use:

1. Select `Game`
2. Choose game language
3. Enter participant fields (`Name`, `ID`, `Age`, `N`, `Note`)
4. Configure stage order and duration, for example (`Relax`, `Break`, `Game`)
5. Launch game and run the session

## Focus Game (N-back)

In `Focus Game`, the examiner sets `N`. The player must always remember the newest `N` letters and press `SPACE` only when the current letter matches the one from `N` steps earlier.

`N_Back_game` is based on: [danghoanganh36/N-Back-Game](https://github.com/danghoanganh36/N-Back-Game).

Example (`N = 3`):

- `A, K, D, A` -> press `SPACE` on the last `A`
- `A, K, D, C` -> do not press
- then memory slides to `K, D, C`, and the rule continues

## Output Files

- EEG/PPG recordings: `EEG_APP/results/`
- Game result CSV: `GAME/n_back/result/`
- Master control workbook: `GAME/n_back/result/Master_Control.xlsx`

## License and Citation

This software is provided for research and academic use.

If you use this software, you **must cite the author** in your publication, report, thesis, or project documentation.

Recommended citation:

`Pham, M. C. EEG Analyse Software (Muse EEG/PPG acquisition and Focus Game), RPTU Kaiserslautern-Landau.`

## Author

👨‍💻 **Author**  
**Manh Cuong Pham**  
📧 mpham@rptu.de
💼 PhD Candidate at RPTU Kaiserslautern-Landau
