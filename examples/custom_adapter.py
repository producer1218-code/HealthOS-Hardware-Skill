"""Minimal external adapter example. Add the repo root and src to PYTHONPATH."""
import json
from pathlib import Path

from healthos.model import Observation


class ExampleSensorAdapter:
    def read(self, path: Path, user_id: str):
        for row in json.loads(path.read_text(encoding="utf-8")):
            yield Observation(
                user_id=user_id,
                timestamp=row["time"],
                metric="resting_heart_rate_bpm",
                value=float(row["resting_hr"]),
                unit="bpm",
                source="example-sensor",
                device_id=row["device"],
                context="synthetic example",
            )
