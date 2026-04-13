from __future__ import annotations

from dataclasses import dataclass, field


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
    stream_name: str = "Muse"
    result_dir: str = "EEG_APP/results"
    plot_update_interval_ms: int = 80
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
    )
    eeg_channels: tuple[EEGChannelConfig, ...] = field(
        default_factory=lambda: (
            EEGChannelConfig(index=0, name="TP9"),
            EEGChannelConfig(index=1, name="AF7"),
            EEGChannelConfig(index=2, name="AF8"),
            EEGChannelConfig(index=3, name="TP10"),
        )
    )

    @property
    def eeg_channel_names(self) -> list[str]:
        return [channel.name for channel in self.eeg_channels]

    @property
    def eeg_channel_count(self) -> int:
        return len(self.eeg_channels)
