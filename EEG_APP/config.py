from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_32_CHANNEL_NAMES = (
    "Fp1",
    "Fp2",
    "F7",
    "F3",
    "Fz",
    "F4",
    "F8",
    "FT7",
    "FC3",
    "FCz",
    "FC4",
    "FT8",
    "T7",
    "C3",
    "Cz",
    "C4",
    "T8",
    "TP7",
    "CP3",
    "CPz",
    "CP4",
    "TP8",
    "P7",
    "P3",
    "Pz",
    "P4",
    "P8",
    "O1",
    "Oz",
    "O2",
    "AF3",
    "AF4",
)

EEGO_CHANNELS = {
    "Fp1": 0,
    "Fp2": 1,
    "F3": 3,
    "F4": 5,
    "C3": 13,
    "Cz": 14,
    "C4": 15,
    "P3": 23,
    "Pz": 24,
    "P4": 25,
    "O1": 27,
    "O2": 29,
}


@dataclass(frozen=True)
class EEGChannelConfig:
    index: int
    name: str
    dead: bool = False


@dataclass(frozen=True)
class AppConfig:
    max_points: int = 1000
    eeg_sampling_rate: int = 256
    ppg_sampling_rate: int = 64
    stream_timeout: int = 10
    stream_name: str = ""
    result_dir: str = "EEG_APP/results"
    plot_update_interval_ms: int = 200
    device_warmup_seconds: float = 2.5
    muselsl_retries: int = 9999
    muselsl_restart_delay_seconds: float = 2.0
    stream_recovery_cooldown_seconds: float = 1.5
    eeg_plot_range_uv: tuple[float, float] = (-200.0, 200.0)
    ppg_plot_range: tuple[float, float] = (-200.0, 200.0)
    eeg_file_prefix: str = "eeg_data"
    ppg_file_prefix: str = "ppg_data"
    reverse_eeg_stream_order: bool = True
    reverse_ppg_stream_order: bool = True
    eeg_colors: tuple[str, ...] = (
        "#ff6b6b",
        "#3b82f6",
        "#f59e0b",
        "#10b981",
        "#a78bfa",
        "#f472b6",
        "#facc15",
        "#34d399",
        "#60a5fa",
        "#fb7185",
        "#2dd4bf",
        "#f97316",
    )
    eeg_channels: tuple[EEGChannelConfig, ...] = field(
        default_factory=lambda: tuple(
            EEGChannelConfig(index=index, name=name) for index, name in enumerate(DEFAULT_32_CHANNEL_NAMES)
        )
    )

    @property
    def eeg_channel_names(self) -> list[str]:
        return [channel.name for channel in self.eeg_channels]

    @property
    def eeg_channel_count(self) -> int:
        return len(self.eeg_channels)

    @property
    def nback_channel_map(self) -> dict[str, int]:
        index_by_name = {channel.name: channel.index for channel in self.eeg_channels}
        return {name: index_by_name[name] for name in EEGO_CHANNELS if name in index_by_name}


def extract_nback_channels(sample_data: list[float] | tuple[float, ...], channel_map: dict[str, int] | None = None) -> dict[str, float]:
    selected = channel_map or EEGO_CHANNELS
    return {
        name: float(sample_data[index])
        for name, index in selected.items()
        if index < len(sample_data)
    }
