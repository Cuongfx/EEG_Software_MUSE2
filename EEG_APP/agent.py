from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureRule:
    name: str
    description: str


class ArchitectureAgent:
    """Project architecture rules for future development."""

    def __init__(self) -> None:
        self.rules = [
            ArchitectureRule(
                name="eeg_boundary",
                description="EEG folder handles device discovery, stream control, filters, processing, session state, persistence, and architecture rules.",
            ),
            ArchitectureRule(
                name="game_boundary",
                description="Game folder handles game registry, game launchers, and one subfolder per game implementation.",
            ),
            ArchitectureRule(
                name="modular_games",
                description="Every game must be implemented as a module so it can be edited or replaced without changing the main UI flow.",
            ),
            ArchitectureRule(
                name="thin_entrypoint",
                description="main.py should stay thin and only start the UI application.",
            ),
        ]

    def list_rules(self) -> list[ArchitectureRule]:
        return list(self.rules)
