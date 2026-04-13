from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class NBackRules:
    actual_minutes: int
    practice_minutes: int
    display_time_ms: int
    intertrial_interval_ms: int
    match_probability_percent: int


def load_rules(path) -> NBackRules:
    raw = path.read_text().strip()
    values = [value.strip() for value in raw.split(",")]
    return NBackRules(
        actual_minutes=int(values[0]),
        practice_minutes=int(values[1]),
        display_time_ms=int(values[2]),
        intertrial_interval_ms=int(values[3]),
        match_probability_percent=int(values[4]),
    )


def calculate_trial_count(duration_minutes: float, display_time_ms: int, intertrial_interval_ms: int) -> int:
    duration_ms = max(duration_minutes, 0.1) * 60 * 1000
    step_ms = max(display_time_ms + intertrial_interval_ms, 1)
    return max(1, math.floor(duration_ms / step_ms))
