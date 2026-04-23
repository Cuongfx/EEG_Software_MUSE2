from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

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
    *,
    user_id: str = "unknown",
    device_id: str = "unknown_device",
    session_label: str = "ABC",
) -> SavedSessionFiles | None:
    timestamp = timestamp or datetime.now()
    date_stamp = timestamp.strftime("%Y%m%d")
    time_stamp = timestamp.strftime("%H%M%S")
    result_dir = Path(config.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    with state.data_lock:
        eeg_rows = list(state.recorded_eeg)
        ppg_rows = list(state.recorded_ppg)

    if not eeg_rows and not ppg_rows:
        return None

    safe_user_id = _safe_participant_file_id(user_id)
    safe_device_id = _safe_filename_token(device_id, fallback="unknown_device")
    safe_session_label = _safe_session_label(session_label)

    eeg_path = result_dir / f"{safe_user_id}_EEG_{safe_device_id}_{date_stamp}_{time_stamp}_{safe_session_label}.csv"
    with eeg_path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", *config.eeg_channel_names])
        writer.writerows(eeg_rows)

    ppg_path: Path | None = None
    if ppg_rows:
        ppg_path = result_dir / f"{safe_user_id}_PPG_{safe_device_id}_{date_stamp}_{time_stamp}_{safe_session_label}.csv"
        with ppg_path.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Timestamp", "LUX", "IR", "RED", "PPG_raw", "PPG_filtered", "HR_BPM"]
            )
            writer.writerows(ppg_rows)

    return SavedSessionFiles(eeg_path=eeg_path, ppg_path=ppg_path)


def _safe_filename_token(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip())
    return cleaned or fallback


def _safe_participant_file_id(value: str) -> str:
    raw = str(value).strip()
    if raw.upper().startswith("P"):
        raw = raw[1:]
    cleaned_digits = re.sub(r"[^0-9]+", "", raw)
    return f"P{cleaned_digits}" if cleaned_digits else "Punknown"


def _safe_session_label(value: str) -> str:
    labels = [character for character in str(value).upper() if character in {"A", "B", "C"}]
    return "_".join(labels) if labels else "A_B_C"
