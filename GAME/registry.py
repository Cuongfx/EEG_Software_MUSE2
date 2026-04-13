from __future__ import annotations

import subprocess
import sys
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GameDefinition:
    game_id: str
    title: str
    description: str
    module_path: Path
    module_name: str
    owner: str | None = None
    source: str | None = None


class GameRegistry:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.games = self._build_games()

    def list_games(self) -> list[GameDefinition]:
        return list(self.games.values())

    def get(self, game_id: str) -> GameDefinition:
        return self.games[game_id]

    def launch(self, game_id: str) -> subprocess.Popen[str]:
        game = self.get(game_id)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        return subprocess.Popen(
            [sys.executable, "-m", game.module_name],
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
        )

    def _build_games(self) -> dict[str, GameDefinition]:
        n_back_path = self.project_root / "GAME" / "n_back" / "main.py"
        return {
            "n_back": GameDefinition(
                game_id="n_back",
                title="Focus Game",
                description="Launch the bundled focus task in a separate game window.",
                module_path=n_back_path,
                module_name="GAME.n_back.main",
                owner=None,
                source="Bundled locally in GAME/n_back. No verifiable upstream author metadata was found in the provided files.",
            )
        }
