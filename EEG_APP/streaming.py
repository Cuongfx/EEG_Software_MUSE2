from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

import mne_lsl.lsl
import numpy as np

from .config import AppConfig
from .processing import SignalProcessor
from .state import SessionState
from .storage import SavedSessionFiles, save_session_data


def resolve_stream(stype: str, timeout: int, name: str, required: bool = True):
    streams = mne_lsl.lsl.resolve_streams(stype=stype, timeout=timeout)
    if name:
        streams = [stream for stream in streams if stream.name == name]
    if streams:
        return streams[0]
    if required:
        raise RuntimeError(f"Could not find LSL stream for type '{stype}'.")
    return None


@dataclass(frozen=True)
class ControllerStatus:
    running: bool
    eeg_samples: int
    ppg_samples: int
    eeg_connected: bool
    ppg_connected: bool
    recording: bool


class MuseStreamController:
    def __init__(
        self,
        config: AppConfig,
        state: SessionState,
        processor: SignalProcessor,
        status_sink: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config
        self.state = state
        self.processor = processor
        self.status_sink = status_sink or print
        self.running = False
        self.reader_thread: threading.Thread | None = None
        self.eeg_inlet = None
        self.ppg_inlet = None
        self.eeg_channel_map: list[int] | None = None
        self.eeg_channel_labels: list[str] = []
        self._eeg_mapping_logged = False
        self._last_recovery_attempt = 0.0
        self._save_context: dict[str, str] = {"user_id": "unknown", "device_id": "unknown_device", "session_label": "ABC"}

    def start(self) -> None:
        if self.running:
            return
        self.processor.reset_session()
        self._emit("Looking for Muse LSL streams...")

        eeg_stream = resolve_stream("EEG", self.config.stream_timeout, self.config.stream_name, True)
        self.eeg_inlet = mne_lsl.lsl.StreamInlet(eeg_stream)
        self.eeg_inlet.open_stream()
        self.eeg_inlet.flush()
        self._configure_eeg_mapping()

        ppg_stream = resolve_stream("PPG", 2, self.config.stream_name, False)
        if ppg_stream is not None:
            self.ppg_inlet = mne_lsl.lsl.StreamInlet(ppg_stream)
            self.ppg_inlet.open_stream()
            self.ppg_inlet.flush()
            self._emit("Connected to EEG and PPG streams.")
        else:
            self.ppg_inlet = None
            self._emit("Connected to EEG stream. No PPG stream found.")

        self.running = True
        self.reader_thread = threading.Thread(target=self._reader_loop, name="muse-lsl-reader", daemon=True)
        self.reader_thread.start()
        self._emit("Receiving live Muse data over LSL...")

    def stop(self, save: bool = True) -> SavedSessionFiles | None:
        if not self.running and self.eeg_inlet is None:
            return None
        self.running = False
        self._emit("Stopping data...")
        if self.reader_thread is not None:
            self.reader_thread.join(timeout=1.0)
            self.reader_thread = None
        self._close_streams()
        if not save:
            return None

        saved_files = save_session_data(
            self.config,
            self.state,
            user_id=self._save_context["user_id"],
            device_id=self._save_context["device_id"],
            session_label=self._save_context["session_label"],
        )
        if saved_files is None:
            self._emit("No recorded data to save.")
        elif saved_files.ppg_path is not None:
            self._emit(f"Saved to {saved_files.eeg_path} and {saved_files.ppg_path}")
        else:
            self._emit(f"Saved to {saved_files.eeg_path}")
        self.clear_save_context()
        return saved_files

    def start_recording(self) -> None:
        self.state.start_recording()
        self._emit("Recording started.")

    def stop_recording(self, save: bool = True) -> SavedSessionFiles | None:
        self.state.stop_recording()
        self._emit("Recording stopped.")
        if not save:
            return None
        saved_files = save_session_data(
            self.config,
            self.state,
            user_id=self._save_context["user_id"],
            device_id=self._save_context["device_id"],
            session_label=self._save_context["session_label"],
        )
        if saved_files is None:
            self._emit("No recorded data to save.")
        elif saved_files.ppg_path is not None:
            self._emit(f"Saved to {saved_files.eeg_path} and {saved_files.ppg_path}")
        else:
            self._emit(f"Saved to {saved_files.eeg_path}")
        self.clear_save_context()
        return saved_files

    def set_save_context(self, *, user_id: str, device_id: str, session_label: str) -> None:
        self._save_context = {
            "user_id": str(user_id or "unknown"),
            "device_id": str(device_id or "unknown_device"),
            "session_label": str(session_label or "ABC"),
        }

    def clear_save_context(self) -> None:
        self._save_context = {"user_id": "unknown", "device_id": "unknown_device", "session_label": "ABC"}

    def status(self) -> ControllerStatus:
        with self.state.data_lock:
            return ControllerStatus(
                running=self.running,
                eeg_samples=len(self.state.recorded_eeg),
                ppg_samples=len(self.state.recorded_ppg),
                eeg_connected=self.eeg_inlet is not None,
                ppg_connected=self.ppg_inlet is not None,
                recording=self.state.recording_enabled,
            )

    def _reader_loop(self) -> None:
        while self.running:
            try:
                saw_data = False

                if self.eeg_inlet is not None:
                    eeg_samples, eeg_times = self.eeg_inlet.pull_chunk(timeout=0.0, max_samples=32)
                    if len(eeg_times) > 0:
                        eeg_samples_np = np.asarray(eeg_samples, dtype=float)
                        if eeg_samples_np.ndim == 1:
                            eeg_samples_np = eeg_samples_np[np.newaxis, :]
                        eeg_samples_np = self._normalize_eeg_samples(eeg_samples_np)
                        self.processor.process_eeg_chunk(eeg_samples_np, eeg_times)
                        saw_data = True

                if self.ppg_inlet is not None:
                    ppg_samples, ppg_times = self.ppg_inlet.pull_chunk(timeout=0.0, max_samples=48)
                    if len(ppg_times) > 0:
                        ppg_samples_np = np.asarray(ppg_samples, dtype=float)
                        if ppg_samples_np.ndim == 1:
                            ppg_samples_np = ppg_samples_np[np.newaxis, :]
                        if self.config.reverse_ppg_stream_order:
                            ppg_samples_np = ppg_samples_np[:, ::-1]
                        self.processor.process_ppg_chunk(ppg_samples_np, ppg_times)
                        saw_data = True

                if not saw_data:
                    time.sleep(0.01)
            except Exception as exc:
                if not self.running:
                    break
                self._emit(f"LSL read issue detected: {exc}. Attempting stream recovery...")
                self._recover_streams()
                time.sleep(0.25)

    def _close_streams(self) -> None:
        if self.eeg_inlet is not None:
            self.eeg_inlet.close_stream()
            self.eeg_inlet = None
        self.eeg_channel_map = None
        self.eeg_channel_labels = []
        self._eeg_mapping_logged = False
        if self.ppg_inlet is not None:
            self.ppg_inlet.close_stream()
            self.ppg_inlet = None

    def _emit(self, message: str) -> None:
        self.status_sink(message)

    def _recover_streams(self) -> None:
        now = time.time()
        if now - self._last_recovery_attempt < self.config.stream_recovery_cooldown_seconds:
            return
        self._last_recovery_attempt = now

        try:
            self._close_streams()
        except Exception:
            pass

        try:
            eeg_stream = resolve_stream("EEG", self.config.stream_timeout, self.config.stream_name, True)
            self.eeg_inlet = mne_lsl.lsl.StreamInlet(eeg_stream)
            self.eeg_inlet.open_stream()
            self.eeg_inlet.flush()
            self._configure_eeg_mapping()

            ppg_stream = resolve_stream("PPG", 2, self.config.stream_name, False)
            if ppg_stream is not None:
                self.ppg_inlet = mne_lsl.lsl.StreamInlet(ppg_stream)
                self.ppg_inlet.open_stream()
                self.ppg_inlet.flush()
            else:
                self.ppg_inlet = None
            self._emit("LSL stream recovery completed.")
        except Exception as exc:
            self._emit(f"LSL stream recovery is waiting for the Muse stream to return. ({exc})")

    def _configure_eeg_mapping(self) -> None:
        self.eeg_channel_map = None
        self.eeg_channel_labels = []
        self._eeg_mapping_logged = False
        if self.eeg_inlet is None:
            return

        try:
            sinfo = self.eeg_inlet.get_sinfo(timeout=2.0)
            channel_names = sinfo.get_channel_names() or []
        except Exception as exc:
            self._emit(f"EEG metadata unavailable, using fallback channel order. ({exc})")
            return

        self.eeg_channel_labels = [str(name) for name in channel_names if name is not None]
        if not self.eeg_channel_labels:
            self._emit("EEG stream has no channel labels, using fallback channel order.")
            return

        normalized_source = [self._normalize_channel_name(name) for name in self.eeg_channel_labels]
        mapping: list[int] = []
        missing_labels: list[str] = []
        for channel in self.config.eeg_channels:
            wanted = self._normalize_channel_name(channel.name)
            try:
                mapping.append(normalized_source.index(wanted))
            except ValueError:
                missing_labels.append(channel.name)

        if missing_labels:
            labels = ", ".join(self.eeg_channel_labels)
            missing = ", ".join(missing_labels)
            self._emit(
                f"EEG labels found [{labels}], but missing [{missing}]. Using fallback channel order."
            )
            return

        self.eeg_channel_map = mapping
        labels = ", ".join(self.eeg_channel_labels)
        ordered = ", ".join(self.config.eeg_channel_names)
        self._emit(f"EEG channel mapping ready. Source labels: [{labels}] -> UI order: [{ordered}]")

    def _normalize_eeg_samples(self, samples: np.ndarray) -> np.ndarray:
        expected_channels = self.config.eeg_channel_count

        if self.eeg_channel_map is not None:
            max_index = max(self.eeg_channel_map, default=-1)
            if max_index < samples.shape[1]:
                mapped = samples[:, self.eeg_channel_map]
                if not self._eeg_mapping_logged:
                    self._emit(
                        "Using EEG channel labels for plotting order: "
                        + ", ".join(self.config.eeg_channel_names)
                    )
                    self._eeg_mapping_logged = True
                return mapped
            self._emit("EEG channel map no longer matches stream width. Reverting to fallback order.")
            self.eeg_channel_map = None

        fallback = samples[:, ::-1] if self.config.reverse_eeg_stream_order else samples
        if fallback.shape[1] > expected_channels:
            fallback = fallback[:, :expected_channels]
        elif fallback.shape[1] < expected_channels:
            padded = np.zeros((fallback.shape[0], expected_channels), dtype=float)
            padded[:, : fallback.shape[1]] = fallback
            fallback = padded

        if not self._eeg_mapping_logged:
            source_labels = ", ".join(self.eeg_channel_labels) if self.eeg_channel_labels else "unavailable"
            self._emit(
                "Using fallback EEG order from archived Muse flow. "
                f"Source labels: [{source_labels}]"
            )
            self._eeg_mapping_logged = True
        return fallback

    @staticmethod
    def _normalize_channel_name(name: str) -> str:
        normalized = "".join(char for char in name.upper() if char.isalnum())
        if normalized in {"AUX", "RIGHTAUX"}:
            return "AUX"
        return normalized
