"""Canonical observation model and explicit unit/metric vocabulary."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import isfinite


# An intentionally small ontology: add metrics with explicit units and aggregation.
METRICS = {
    "resting_heart_rate_bpm": ("bpm", "median"),
    "heart_rate_bpm": ("bpm", "median"),
    "hrv_rmssd_ms": ("ms", "median"),
    "hrv_sdnn_ms": ("ms", "median"),
    "sleep_minutes": ("min", "median"),
    "steps_count": ("count", "max"),  # each record is a cumulative daily total
    "spo2_pct": ("%", "median"),
    "skin_temp_c": ("degC", "median"),
    "respiratory_rate_bpm": ("breaths/min", "median"),
    "self_report_energy_0_10": ("score", "median"),
}


def parse_timestamp(value: str) -> datetime:
    if not value or not isinstance(value, str):
        raise ValueError("timestamp is required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamp must contain a timezone offset")
    return result


@dataclass(frozen=True)
class Observation:
    user_id: str
    timestamp: str
    metric: str
    value: float
    unit: str
    source: str
    device_id: str
    quality: float = 1.0
    context: str = ""

    def __post_init__(self) -> None:
        if not self.user_id or not self.source or not self.device_id:
            raise ValueError("user_id, source and device_id are required")
        parse_timestamp(self.timestamp)
        if self.metric not in METRICS:
            raise ValueError(f"unsupported metric: {self.metric}")
        if self.unit != METRICS[self.metric][0]:
            raise ValueError(f"{self.metric} requires unit {METRICS[self.metric][0]}")
        if not isfinite(float(self.value)):
            raise ValueError("value must be finite")
        if not 0 <= float(self.quality) <= 1:
            raise ValueError("quality must be between 0 and 1")
        if self.metric == "spo2_pct" and not 0 <= self.value <= 100:
            raise ValueError("SpO2 percentage outside 0-100")
        if self.metric in ("sleep_minutes", "steps_count") and self.value < 0:
            raise ValueError("duration and steps cannot be negative")
        if self.metric == "self_report_energy_0_10" and not 0 <= self.value <= 10:
            raise ValueError("self-reported energy outside 0-10")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Observation":
        return cls(
            user_id=str(data["user_id"]),
            timestamp=str(data["timestamp"]),
            metric=str(data["metric"]),
            value=float(data["value"]),
            unit=str(data["unit"]),
            source=str(data["source"]),
            device_id=str(data["device_id"]),
            quality=float(data.get("quality", 1.0)),
            context=str(data.get("context", "")),
        )
