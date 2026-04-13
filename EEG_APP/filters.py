from __future__ import annotations

import numpy as np
import scipy.signal


class WindowIIRNotchFilter:
    def __init__(self, w0: float, q: float, fs: float) -> None:
        self.b, self.a = scipy.signal.iirnotch(w0, q, fs=fs)
        self.z = scipy.signal.lfilter_zi(self.b, self.a)

    def filter_data(self, values: list[float] | np.ndarray) -> np.ndarray:
        if len(values) == 0:
            return np.array(values)
        result, self.z = scipy.signal.lfilter(self.b, self.a, values, zi=self.z)
        return np.array(result)


class DCBlockingFilter:
    def __init__(self, alpha: float = 0.99) -> None:
        self.b = [1, -1]
        self.a = [1, -alpha]
        self.zi = scipy.signal.lfilter_zi(self.b, self.a)

    def filter_data(self, values: list[float] | np.ndarray) -> np.ndarray:
        if len(values) == 0:
            return np.array(values)
        result, self.zi = scipy.signal.lfilter(self.b, self.a, values, zi=self.zi)
        return np.array(result)


class WindowButterBandpassFilter:
    def __init__(self, order: int, low: float, high: float, fs: float) -> None:
        self.b, self.a = scipy.signal.butter(order, [low, high], btype="band", fs=fs)
        self.z = scipy.signal.lfilter_zi(self.b, self.a)

    def filter_data(self, values: list[float] | np.ndarray) -> np.ndarray:
        values = np.reshape(values, (-1,))
        result, self.z = scipy.signal.lfilter(self.b, self.a, values, zi=self.z)
        return np.array(result)


class WindowFilter:
    def __init__(self, filters: list[object]) -> None:
        self.filters = filters

    def filter_data(self, values: list[float] | np.ndarray) -> np.ndarray:
        filtered = values
        for filter_instance in self.filters:
            filtered = filter_instance.filter_data(filtered)
        return filtered


def create_filter_chain_eeg(fs: int) -> WindowFilter:
    return WindowFilter(
        [
            DCBlockingFilter(alpha=0.99),
            WindowIIRNotchFilter(50.0, 5.0, fs),
            WindowButterBandpassFilter(order=4, low=0.5, high=35.0, fs=fs),
        ]
    )


def create_filter_chain_ppg(fs: int) -> WindowFilter:
    return WindowFilter(
        [
            DCBlockingFilter(alpha=0.99),
            WindowButterBandpassFilter(order=4, low=0.5, high=5.0, fs=fs),
        ]
    )
