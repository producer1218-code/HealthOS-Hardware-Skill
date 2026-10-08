"""Streaming parser for selected Apple Health export.xml quantity Records."""
from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import iterparse

from healthos.model import METRICS, Observation


APPLE_TYPES = {
    "HKQuantityTypeIdentifierHeartRate": ("heart_rate_bpm", "count/min"),
    "HKQuantityTypeIdentifierRestingHeartRate": ("resting_heart_rate_bpm", "count/min"),
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": ("hrv_sdnn_ms", "ms"),
    "HKQuantityTypeIdentifierOxygenSaturation": ("spo2_pct", "%"),
    "HKQuantityTypeIdentifierAppleSleepingWristTemperature": ("skin_temp_c", "degC"),
    "HKQuantityTypeIdentifierStepCount": ("steps_count", "count"),
}


class AppleHealthExport:
    def read(self, path: Path, user_id: str):
        # Apple exports may be large; clear each Record after it is handled.
        for _, element in iterparse(path, events=("end",)):
            if element.tag != "Record":
                continue
            try:
                kind = element.get("type", "")
                if kind not in APPLE_TYPES:
                    continue
                metric, apple_unit = APPLE_TYPES[kind]
                if element.get("unit") != apple_unit:
                    continue
                value = float(element.attrib["value"])
                if metric == "spo2_pct" and 0 <= value <= 1:
                    value *= 100
                if metric == "steps_count":
                    # Interval step counts cannot safely become cumulative daily totals.
                    # Preserve no value here until an interval-aware aggregator exists.
                    continue
                yield Observation(
                    user_id=user_id,
                    timestamp=element.attrib["endDate"].replace(" ", "T", 1),
                    metric=metric,
                    value=value,
                    unit=METRICS[metric][0],
                    source="apple-health-export",
                    device_id=element.get("sourceName", "unknown"),
                    context="exported_quantity_record",
                )
            finally:
                element.clear()
