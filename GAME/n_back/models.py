from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SessionStage:
    kind: str
    duration_minutes: float
    order: int


@dataclass
class ExaminerSession:
    participant_name: str
    participant_id: str
    device_id: str
    age: str
    n_value: int
    relax_audio_enabled: bool
    relax_music_track: str
    announcement_volume: float
    note: str
    block_plan: list[int]
    session_stages: list[SessionStage]


@dataclass
class TrialResult:
    letter: str
    match_or_not_match: str
    timestamp_letter_appeared: float
    timestamp_letter_disappeared: float | None
    is_key_pressed: str
