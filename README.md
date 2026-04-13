# EEG Analyse

`EEG Analyse` is a desktop application for working with a Muse headset, viewing live EEG and PPG signals, recording data, and running an examiner-controlled cognitive task called `Focus Game`.

The software is organized into three active folders:

- `UI` for the desktop interface
- `EEG_APP` for device connection, streaming, processing, and recording
- `GAME` for the game launcher and modular game implementations

`main.py` is the only file you need to run.

## Features

- Connect to a Muse device from inside the software
- Start the internal `muselsl` stream with PPG enabled
- View live EEG and PPG plots
- Record EEG and PPG data to CSV
- Launch `Focus Game` from the app UI
- Run examiner-controlled session blocks with `Relax`, `Game`, and `Break`
- Save participant and score information to `Master_Control.xlsx`

## Project Structure

```text
EEG/
├── UI/
│   ├── app.py
│   ├── dialogs.py
│   ├── main_window.py
│   └── widgets.py
├── EEG_APP/
│   ├── agent.py
│   ├── config.py
│   ├── device.py
│   ├── filters.py
│   ├── processing.py
│   ├── state.py
│   ├── storage.py
│   └── streaming.py
├── GAME/
│   ├── registry.py
│   └── n_back/
│       ├── config.py
│       ├── data.py
│       ├── game.py
│       ├── main.py
│       ├── master_control.py
│       ├── models.py
│       ├── participant-task.csv
│       ├── rules.txt
│       └── result/
├── Archieve/
├── .venv/
└── main.py
```

## Architecture Rules

The project includes an internal architecture/rules module in [EEG_APP/agent.py](/Users/manhcuongfx/Desktop/EEG/EEG_APP/agent.py:1).

Design rules:

- `UI` handles windows, dialogs, widgets, layout, and user interaction only.
- `EEG_APP` handles Muse discovery, streaming, EEG/PPG processing, device control, and file saving.
- `GAME` handles the game registry and one folder per game.
- Each game should stay modular so it can be changed independently later.
- `main.py` should stay thin and only launch the app.

## Requirements

Typical environment:

- Python 3.12
- Muse headset
- `muselsl`
- PyQt6 for the main application UI
- Tkinter for the current `Focus Game` window

If you use the provided virtual environment, activate it before running the software.

## Run The Software

From the project root:

```bash
python main.py
```

You do not need to manually start `muselsl stream --ppg` in another terminal. The software starts and manages the Muse stream internally after you connect a device.

## Main UI Workflow

When the app opens, you will see the main `EEG Analyse` window.

Typical workflow:

1. Click `Connect to Device`
2. Choose the Muse device from the connection dialog
3. Wait for the stream to connect
4. Watch the live EEG and PPG plots
5. Click `Record Data` if you want to manually record a session
6. Click `Stop Recording` to save the current EEG and PPG data
7. Click `Disconnect Device` when finished

The UI also includes:

- a game selector dropdown
- a button to open the selected game in a separate window
- device status information
- battery status if available from the device/backend
- session log messages

## Recording Behavior

There are two main ways recording can happen:

### Manual recording

- Connect a Muse device
- Click `Record Data`
- The app records EEG and PPG data
- Click `Stop Recording` to save the files

### Game-linked recording

- Connect a Muse device
- Open `Focus Game`
- The examiner confirms the block plan
- The participant clicks `Start`
- Recording starts at the beginning of the block
- Recording stops automatically after the full block finishes

Recorded files are saved in [EEG_APP/results](/Users/manhcuongfx/Desktop/EEG/EEG_APP/results).

Typical filenames:

- `eeg_data_YYYYMMDD_HHMMSS.csv`
- `ppg_data_YYYYMMDD_HHMMSS.csv`

## Muse Device Connection

The software scans for Muse devices and starts the internal `muselsl` stream with PPG.

Notes:

- The app supports different Muse identifier styles, including UUID-style values seen on macOS and classic MAC-style addresses.
- The app includes retry and reconnect logic around the `muselsl` subprocess and LSL stream reads.
- If the stream drops temporarily, the software attempts to recover instead of failing immediately.

## Focus Game

`Focus Game` is the currently available game in the software. Internally it lives in the `GAME/n_back` module, but the user-facing name is `Focus Game`.

When the game is opened, two windows appear:

- a participant-facing game window
- a separate `Examiner Control` window

### Examiner Control

The examiner enters:

- `Name`
- `ID`
- `Age`
- `Note`

The examiner also sets the session block plan:

- `Relax`
- `Game`
- `Break`

For each session, the examiner chooses:

- order in the block
- duration in minutes

The examiner then clicks `Confirm Session`.

### Participant Flow

Before confirmation, the participant window shows:

- `Waiting for Examiner...`

After the examiner confirms, the participant sees a `Start` button.

When the participant clicks `Start`:

- the full block begins
- recording starts
- the block follows the examiner’s order exactly

Example:

- if the examiner sets `Relax -> Game -> Break`
- the participant will go through `Relax`, then `Game`, then `Break`

### Session Messages

During guided stages, the participant sees:

- `Please relax untill you hear the sound`
- `Please Break untill you hear the sound`

For the game stage:

- an introduction is shown first
- the participant presses `SPACE` to move through the game instructions
- after the final instruction page, the actual game begins

### Sounds

After each session ends, the app plays a double `bip bip` style system bell:

- after `Relax`
- after `Game`
- after `Break`

### End Of Block

When the full block is finished:

- recording stops automatically
- the participant window shows:
  - `Congratulation, the Block is ended`
  - `The Experiment is finished. Thank you for your attention!`

## Focus Game Outputs

### Session CSV

The game exports a CSV file into [GAME/n_back/result](/Users/manhcuongfx/Desktop/EEG/GAME/n_back/result).

Filename format:

```text
(participant_id)_(YYYY-MM-DD)_(arrangement).csv
```

Arrangement code:

- `A` = Relax
- `B` = Game
- `C` = Break

Examples:

- `10_2026-04-13_ABC.csv`
- `13_2026-04-13_CBA.csv`

### Master Control Workbook

The examiner summary is appended to:

[GAME/n_back/result/Master_Control.xlsx](/Users/manhcuongfx/Desktop/EEG/GAME/n_back/result/Master_Control.xlsx)

Each completed game appends a new row. The file is not overwritten.

Columns:

- `Name`
- `ID`
- `Age`
- `score`
- `Note`

## Participant Task Data

The game reads participant task definitions from:

[GAME/n_back/participant-task.csv](/Users/manhcuongfx/Desktop/EEG/GAME/n_back/participant-task.csv)

If a participant ID is not found there, the software generates a fallback block plan instead of stopping with an error.

## Archived Files

`Archieve/` is kept for legacy reference only.

Examples:

- old Muse scripts
- older game source

The active software should be run from `main.py`, not from archived files.

## Attribution Note

The current `Focus Game` was rebuilt from the bundled local N-back game files that were previously stored in the project.

I could not verify a reliable original upstream owner from the available local files because there was no clear author header, license file, or verified upstream repository link in the archived source. Because of that, this README avoids assigning ownership incorrectly.
