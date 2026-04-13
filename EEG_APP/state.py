from __future__ import annotations

import threading
from collections import deque
from datetime import datetime

from .config import AppConfig


class SessionState:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.data_lock = threading.Lock()
        self.eeg_raw_buffers = [
            deque(maxlen=config.max_points) for _ in range(config.eeg_channel_count)
        ]
        self.eeg_buffers = [
            deque(maxlen=config.max_points) for _ in range(config.eeg_channel_count)
        ]
        self.ppg_buffer = deque(maxlen=config.max_points)
        self.ppg_filtered_buffer = deque(maxlen=config.max_points)
        self.heart_rate_buffer = deque(maxlen=config.max_points)
        self.timestamps = deque(maxlen=config.max_points)
        self.recorded_eeg: list[list[float]] = []
        self.recorded_ppg: list[list[float]] = []
        self.recording_enabled = False
        self.recording_started_at: datetime | None = None

    def clear(self) -> None:
        with self.data_lock:
            for buffer in self.eeg_raw_buffers:
                buffer.clear()
            for buffer in self.eeg_buffers:
                buffer.clear()
            self.ppg_buffer.clear()
            self.ppg_filtered_buffer.clear()
            self.heart_rate_buffer.clear()
            self.timestamps.clear()
            self.recording_enabled = False
            self.recording_started_at = None
            self.recorded_eeg.clear()
            self.recorded_ppg.clear()

    def clear_recordings(self) -> None:
        with self.data_lock:
            self.recorded_eeg.clear()
            self.recorded_ppg.clear()

    def start_recording(self) -> None:
        with self.data_lock:
            self.recorded_eeg.clear()
            self.recorded_ppg.clear()
            self.recording_enabled = True
            self.recording_started_at = datetime.now()

    def stop_recording(self) -> None:
        with self.data_lock:
            self.recording_enabled = False

    def has_recorded_data(self) -> bool:
        with self.data_lock:
            return bool(self.recorded_eeg or self.recorded_ppg)
