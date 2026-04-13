from __future__ import annotations

import csv
from pathlib import Path


def load_participant_tasks(path: Path) -> dict[int, list[int]]:
    if not path.exists():
        return {}
    with path.open("r", newline="") as file:
        reader = csv.DictReader(file)
        expected_columns = ["participant_id"] + [f"block_{index}" for index in range(1, 6)]
        if not set(expected_columns).issubset(reader.fieldnames or []):
            raise ValueError("participant-task.csv is missing required columns.")
        tasks: dict[int, list[int]] = {}
        for row in reader:
            participant_id = int(row["participant_id"])
            tasks[participant_id] = [int(row[f"block_{index}"]) for index in range(1, 6)]
        return tasks


def resolve_block_plan(
    participant_id: str,
    tasks: dict[int, list[int]],
    total_blocks: int,
) -> list[int]:
    cleaned_id = participant_id.strip()
    if cleaned_id.isdigit():
        numeric_id = int(cleaned_id)
        if numeric_id in tasks:
            return tasks[numeric_id][:total_blocks]
        start_offset = (numeric_id - 1) % 5
    else:
        seed = sum((index + 1) * ord(char) for index, char in enumerate(cleaned_id))
        start_offset = seed % 5 if cleaned_id else 0

    return [((start_offset + block_index) % 5) + 1 for block_index in range(total_blocks)]
