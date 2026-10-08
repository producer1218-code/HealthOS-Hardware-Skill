"""Parse locally saved WHOOP v2 recovery/sleep API response JSON."""
from __future__ import annotations

import json
from pathlib import Path

from healthos.model import METRICS, Observation


class WhoopV2JSON:
    def read(self, path: Path, user_id: str):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("kind") not in {"recovery", "sleep"}:
            raise ValueError('WHOOP file requires {"kind":"recovery|sleep","records":[...]}')
        records = payload.get("records", [])
        if not isinstance(records, list):
            raise ValueError("WHOOP records must be a list")
        kind = payload["kind"]
        for record in records:
            if record.get("score_state") != "SCORED" or not isinstance(record.get("score"), dict):
                continue
            score = record["score"]
            timestamp = record.get("end") or record.get("created_at")
            if not timestamp:
                continue
            device = "whoop-v2"
            if kind == "recovery":
                fields = {
                    "resting_heart_rate": "resting_heart_rate_bpm",
                    "hrv_rmssd_milli": "hrv_rmssd_ms",
                    "spo2_percentage": "spo2_pct",
                    "skin_temp_celsius": "skin_temp_c",
                }
                for field, metric in fields.items():
                    if score.get(field) is not None:
                        yield Observation(user_id, timestamp, metric, float(score[field]), METRICS[metric][0], "whoop-v2-api", device, context="recovery_score")
            else:
                if record.get("nap"):
                    continue
                summary = score.get("stage_summary") or {}
                parts = ("total_light_sleep_time_milli", "total_slow_wave_sleep_time_milli", "total_rem_sleep_time_milli")
                if all(summary.get(part) is not None for part in parts):
                    minutes = sum(float(summary[part]) for part in parts) / 60000
                    yield Observation(user_id, timestamp, "sleep_minutes", minutes, "min", "whoop-v2-api", device, context="sum_of_sleep_stages")
                if score.get("respiratory_rate") is not None:
                    metric = "respiratory_rate_bpm"
                    yield Observation(user_id, timestamp, metric, float(score["respiratory_rate"]), METRICS[metric][0], "whoop-v2-api", device, context="sleep_score")
