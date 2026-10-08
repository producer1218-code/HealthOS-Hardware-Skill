"""Experimental saved Google Health v4 Fitbit daily RHR subset; no API calls.

Reference: https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints
Civil dates are represented by local noon, not falsely labelled measurement times.
"""
from datetime import date
import json
from pathlib import Path

from healthos.model import Observation


class GoogleHealthRestingHeartRate:
    def read(self, path: Path, user_id: str):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload.get("points"), list):
            raise ValueError("saved snapshot requires points list")
        for point in payload["points"]:
            provenance = point.get("dataSource", {})
            record = point.get("dailyRestingHeartRate", {})
            device = provenance.get("device", {}).get("displayName")
            method = record.get("dailyRestingHeartRateMetadata", {}).get("calculationMethod")
            if provenance.get("platform") != "FITBIT" or not device or not method or not record.get("date"):
                continue
            d = record["date"]
            day = date(d["year"], d["month"], d["day"])
            yield Observation(user_id, day.isoformat() + "T12:00:00+08:00",
                              "resting_heart_rate_bpm", float(record["beatsPerMinute"]), "bpm",
                              "google-health/FITBIT/" + method, "display-name:" + device,
                              context="civil-day anchor Asia/Shanghai; device display name is provisional; quality is parsing integrity")
