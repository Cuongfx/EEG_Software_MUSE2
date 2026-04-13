# Muse Live Studio

This project is now rebuilt around three active folders:

- `UI` for user interface code
- `EEG_APP` for device, signal, streaming, saving, and architecture rules
- `GAME` for game registry and game modules

`Archieve` is kept as legacy reference. `.venv` is unchanged.

## Run

```bash
python main.py
```

## Architecture Rules

The project includes an architecture agent in [EEG_APP/agent.py](/Users/manhcuongfx/Desktop/EEG/EEG_APP/agent.py:1).

Rules:

- `UI` handles windows, dialogs, widgets, styling, and user interaction only.
- `EEG_APP` handles Muse discovery, stream startup, LSL reading, filtering, processing, state, and CSV export.
- `GAME` handles the game registry and one subfolder per game.
- Each game must be modular so it can be edited independently later.
- `main.py` stays thin and only starts the UI app.

## Folder Structure

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
│       └── rules.txt
├── Archieve/
└── main.py
```

## Device Workflow

You only need one running app now.

1. Start the software with `python main.py`
2. Click `Connect to Device`
3. Choose a Muse headset from the device dialog
4. The software starts the internal Muse stream with PPG enabled
5. Click `Record Data` only when you want to begin saving EEG/PPG data
6. Click `Stop Recording` to save the current recording session
7. Click `Disconnect Device` when you want to end the device session

EEG recordings are saved under `EEG_APP/results`.

## Game Workflow

Games are selected from the dropdown in the UI.

Current game:

- `Focus Game`

When launched, the Focus Game now opens with:

- a participant-facing game window
- a separate examiner control window

The participant window stays on `Waiting for Examiner...` until the examiner enters:

- duration
- name
- ID
- age
- note

After confirmation, the participant window unlocks and shows the `Start Game` button.

The examiner-entered information is appended to `GAME/n_back/result/Master_Control.xlsx` with these columns:

- `Name`
- `ID`
- `Age`
- `score`
- `Note`

If a device is connected and recording is not already active, starting a game will automatically start recording for that game session.

If the participant ID is not present in `participant-task.csv`, the game now generates a deterministic fallback block plan instead of failing.

## Stream Stability

The app now launches `muselsl stream` with higher retry counts and includes recovery logic on the LSL reader side.

If the Muse stream drops temporarily, the software will try to:

- let `muselsl` reconnect in the background
- restart the `muselsl` subprocess if it exits unexpectedly
- rebuild the LSL inlets if stream reads fail

## N-Back Attribution

The N-back game was rebuilt as a module from the bundled local game files that were previously stored in `N-Back-Game`.

I could not verify a reliable original upstream owner from the provided files because:

- there was no author header in the source file
- there was no local license or README identifying the original author
- there was no verifiable upstream source link in the project files

Because of that, this README cites it as a bundled local asset rather than assigning ownership incorrectly.
# EEG_Software_MUSE2
