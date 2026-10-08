"""Drop-in adapter example.

Copy this file into your plugin directory (default ``data/private/plugins/``, or a
directory listed in ``HEALTHOS_PLUGIN_PATH``) and reference it from a source as::

    {"id": "my-sensor",
     "adapter": "example_adapter:ExampleSensorAdapter",
     "metrics": ["resting_heart_rate_bpm"],
     "setup_steps": ["导出你自己的 JSON 列表，字段为 time / resting_hr / device。"]}

Then run ``healthos plugins`` to confirm the module was discovered. Plugins are
trusted Python, not a sandbox — inspect them before pointing them at real records.
"""
import json
from pathlib import Path

from healthos.model import Observation


class ExampleSensorAdapter:
    """Reads a JSON list of ``{"time": ..., "resting_hr": ..., "device": ...}`` rows."""

    timezone = "Asia/Shanghai"
    device_id = "example-sensor"

    def configure(self, settings: dict) -> None:
        self.timezone = settings.get("timezone", self.timezone)
        self.device_id = settings.get("device_id", self.device_id)

    def read(self, path: Path, user_id: str):
        for row in json.loads(path.read_text(encoding="utf-8")):
            yield Observation(
                user_id=user_id,
                timestamp=row["time"],
                metric="resting_heart_rate_bpm",
                value=float(row["resting_hr"]),
                unit="bpm",
                source="example-sensor",
                device_id=row.get("device", self.device_id),
                context="synthetic example",
            )
