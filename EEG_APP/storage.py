from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import AppConfig
from .state import SessionState


@dataclass(frozen=True)
class SavedSessionFiles:
    eeg_path: Path
    ppg_path: Path | None = None


def save_session_data(
    config: AppConfig,
    state: SessionState,
    timestamp: datetime | None = None,
) -> SavedSessionFiles | None:
    timestamp = timestamp or datetime.now()
    stamp = timestamp.strftime("%Y%m%d_%H%M%S")
    result_dir = Path(config.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    with state.data_lock:
        eeg_rows = list(state.recorded_eeg)
        ppg_rows = list(state.recorded_ppg)

    if not eeg_rows and not ppg_rows:
        return None

    eeg_path = result_dir / f"{config.eeg_file_prefix}_{stamp}.csv"
    with eeg_path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", *config.eeg_channel_names])
        writer.writerows(eeg_rows)

    ppg_path: Path | None = None
    if ppg_rows:
        ppg_path = result_dir / f"{config.ppg_file_prefix}_{stamp}.csv"
        with ppg_path.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Timestamp", "LUX", "IR", "RED", "PPG_raw", "PPG_filtered", "HR_BPM"]
            )
            writer.writerows(ppg_rows)

    return SavedSessionFiles(eeg_path=eeg_path, ppg_path=ppg_path)
