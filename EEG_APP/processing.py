from __future__ import annotations

import numpy as np
import scipy.signal
from scipy.signal import butter, iirnotch, lfilter

from .config import AppConfig
from .filters import create_filter_chain_eeg, create_filter_chain_ppg
from .state import SessionState


def estimate_hr_from_ppg(ppg_filtered: list[float], fs: int) -> float | None:
    if len(ppg_filtered) < int(fs * 2):
        return None
    window = np.array(ppg_filtered[-int(fs * 30) :])
    peaks, _ = scipy.signal.find_peaks(window, distance=int(0.4 * fs))
    if len(peaks) < 2:
        return None
    rr_intervals = np.diff(peaks) / fs
    bpm = 60.0 / np.mean(rr_intervals)
    return bpm if 35 <= bpm <= 200 else None


def butter_bandpass(lowcut: float, highcut: float, fs: int, order: int = 4):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    return butter(order, [low, high], btype="band")


def bandpass_filter(
    data: np.ndarray,
    lowcut: float = 1.0,
    highcut: float = 40.0,
    fs: int = 256,
    order: int = 4,
) -> np.ndarray:
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    return lfilter(b, a, data)


def notch_filter(data: np.ndarray, freq: float = 50.0, fs: int = 256, q: float = 30.0) -> np.ndarray:
    b, a = iirnotch(freq, q, fs)
    return lfilter(b, a, data)


def filter_eeg_for_display(data: list[float] | np.ndarray, fs: int) -> np.ndarray:
    if len(data) < 10:
        return np.asarray(data, dtype=float)
    filtered = np.asarray(data, dtype=float)
    filtered = notch_filter(filtered, freq=60.0, fs=fs, q=12.0)
    filtered = notch_filter(filtered, freq=50.0, fs=fs, q=5.0)
    filtered = notch_filter(filtered, freq=32.0, fs=fs, q=10.0)
    return bandpass_filter(filtered, lowcut=0.5, highcut=35.0, fs=fs)


class SignalProcessor:
    def __init__(self, config: AppConfig, state: SessionState) -> None:
        self.config = config
        self.state = state
        self.reset_filters()

    def reset_filters(self) -> None:
        self.eeg_filters = [
            create_filter_chain_eeg(self.config.eeg_sampling_rate) if not channel.dead else None
            for channel in self.config.eeg_channels
        ]
        self.ppg_filter = create_filter_chain_ppg(self.config.ppg_sampling_rate)

    def reset_session(self) -> None:
        self.reset_filters()
        self.state.clear()

    def process_eeg_chunk(
        self,
        samples: np.ndarray,
        sample_times: list[float] | np.ndarray,
    ) -> None:
        with self.state.data_lock:
            for sample, sample_time in zip(samples, sample_times):
                row = [float(sample_time)]
                for out_index, channel in enumerate(self.config.eeg_channels):
                    raw_value = float(sample[channel.index]) if channel.index < len(sample) else 0.0
                    self.state.eeg_raw_buffers[out_index].append(raw_value)
                    filtered = self.eeg_filters[out_index].filter_data([raw_value])
                    filtered_value = float(filtered[-1])
                    self.state.eeg_buffers[out_index].append(filtered_value)
                    row.append(raw_value)
                self.state.timestamps.append(float(sample_time))
                if self.state.recording_enabled:
                    self.state.recorded_eeg.append(row)

    def process_ppg_chunk(
        self,
        samples: np.ndarray,
        sample_times: list[float] | np.ndarray,
    ) -> None:
        with self.state.data_lock:
            for sample, sample_time in zip(samples, sample_times):
                if len(sample) < 3:
                    continue
                lux = float(sample[0])
                ir = float(sample[1])
                red = float(sample[2])
                ppg_raw = red - lux
                self.state.ppg_buffer.append(ppg_raw)

                filtered = self.ppg_filter.filter_data([ppg_raw])
                ppg_filtered = float(filtered[-1]) if filtered.size > 0 else 0.0
                self.state.ppg_filtered_buffer.append(ppg_filtered)

                bpm = estimate_hr_from_ppg(
                    list(self.state.ppg_filtered_buffer),
                    self.config.ppg_sampling_rate,
                )
                if bpm is not None:
                    self.state.heart_rate_buffer.append(float(bpm))
                if self.state.recording_enabled:
                    self.state.recorded_ppg.append(
                        [
                            float(sample_time),
                            lux,
                            ir,
                            red,
                            ppg_raw,
                            ppg_filtered,
                            bpm if bpm is not None else float("nan"),
                        ]
                    )
