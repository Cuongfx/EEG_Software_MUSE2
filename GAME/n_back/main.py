from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))
    from GAME.n_back.game import run_game
else:
    from .game import run_game


def run() -> None:
    run_game()


if __name__ == "__main__":
    run()
