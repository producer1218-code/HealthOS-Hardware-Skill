from __future__ import annotations

import csv
from pathlib import Path

from healthos.model import Observation


class CanonicalCSV:
    """Read the documented normalized schema; no vendor credentials required."""

    def read(self, path: Path, user_id: str):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"timestamp", "metric", "value", "unit", "source", "device_id"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError(f"CSV missing columns: {sorted(required - set(reader.fieldnames or []))}")
            for row_number, row in enumerate(reader, 2):
                try:
                    yield Observation.from_dict({**row, "user_id": user_id, "quality": row.get("quality") or 1.0})
                except (ValueError, KeyError) as exc:
                    raise ValueError(f"CSV row {row_number}: {exc}") from exc
