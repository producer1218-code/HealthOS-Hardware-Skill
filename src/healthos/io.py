"""Canonical JSON Lines IO."""
from __future__ import annotations

import json
from pathlib import Path

from healthos.model import Observation


def write_jsonl(path: Path, observations) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for observation in observations:
            handle.write(json.dumps(observation.to_dict(), ensure_ascii=False, allow_nan=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    yield Observation.from_dict(json.loads(line))
                except (ValueError, KeyError, json.JSONDecodeError) as exc:
                    raise ValueError(f"JSONL line {number}: {exc}") from exc
