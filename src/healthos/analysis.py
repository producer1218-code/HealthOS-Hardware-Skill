"""Personal trend research rules; deliberately not a clinical classifier."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

from healthos.model import METRICS, Observation, parse_timestamp


@dataclass(frozen=True)
class Rule:
    direction: str
    min_change: float
    scale_floor: float


# Engineering gates for a demonstration, NOT published clinical thresholds.
RULES = {
    "resting_heart_rate_bpm": Rule("higher", 5.0, 2.5),
    "hrv_rmssd_ms": Rule("lower", 8.0, 5.0),
    "hrv_sdnn_ms": Rule("lower", 8.0, 5.0),
    "sleep_minutes": Rule("lower", 45.0, 25.0),
    "self_report_energy_0_10": Rule("lower", 2.0, 1.0),
}

RULE_VERSION = "baseline-v0.1-research"
MIN_QUALITY = 0.8
BASELINE_DAYS = 28
RECENT_DAYS = 3
MIN_BASELINE_DAYS = 14
Z_GATE = 2.5


def analyze(observations: list[Observation], as_of: date) -> dict:
    """Compare 3 complete local dates with 28 prior dates for each device+metric.

    Changing devices creates a new stream. Missing dates are never filled with zero.
    """
    groups: dict[tuple[str, str, str, str], dict[date, list[float]]] = defaultdict(lambda: defaultdict(list))
    rejected = {"low_quality": 0, "future_or_outside_window": 0}
    for item in observations:
        day = parse_timestamp(item.timestamp).date()
        if item.quality < MIN_QUALITY:
            rejected["low_quality"] += 1
            continue
        if day > as_of or day < as_of - timedelta(days=BASELINE_DAYS + RECENT_DAYS - 1):
            rejected["future_or_outside_window"] += 1
            continue
        groups[(item.user_id, item.source, item.device_id, item.metric)][day].append(item.value)

    results = []
    for (user_id, source, device_id, metric), days in sorted(groups.items()):
        aggregation = METRICS[metric][1]
        daily = {day: (max(values) if aggregation == "max" else median(values)) for day, values in days.items()}
        recent_start = as_of - timedelta(days=RECENT_DAYS - 1)
        baseline_start = recent_start - timedelta(days=BASELINE_DAYS)
        base = [value for day, value in daily.items() if baseline_start <= day < recent_start]
        recent = [value for day, value in daily.items() if recent_start <= day <= as_of]
        result = {
            "user_id": user_id, "source": source, "device_id": device_id,
            "metric": metric, "unit": METRICS[metric][0], "rule_version": RULE_VERSION,
            "baseline_n_days": len(base), "recent_n_days": len(recent),
            "baseline_window": [baseline_start.isoformat(), (recent_start - timedelta(days=1)).isoformat()],
            "recent_window": [recent_start.isoformat(), as_of.isoformat()],
        }
        if len(base) < MIN_BASELINE_DAYS:
            result["status"] = "calibrating"
            result["reason"] = f"need {MIN_BASELINE_DAYS} baseline days for this device and metric"
        elif len(recent) < RECENT_DAYS:
            result["status"] = "insufficient_recent_data"
            result["reason"] = "need one valid observation on each of the last 3 dates"
        else:
            baseline = float(median(base))
            recent_value = float(median(recent))
            result.update(baseline_median=baseline, recent_median=recent_value,
                          delta=recent_value - baseline)
            rule = RULES.get(metric)
            if rule is None:
                result["status"] = "trend_only"
                result["reason"] = "no proactive rule assigned to this metric"
            else:
                mad = float(median(abs(value - baseline) for value in base))
                scale = max(1.4826 * mad, rule.scale_floor)
                directed_change = (recent_value - baseline) * (1 if rule.direction == "higher" else -1)
                result.update(robust_scale=scale, directed_z=directed_change / scale,
                              direction=rule.direction)
                if directed_change >= rule.min_change and directed_change / scale >= Z_GATE:
                    result["status"] = "notable_change"
                    result["reason"] = "persistent change relative to this device's personal baseline; not a diagnosis"
                else:
                    result["status"] = "within_rule_limits"
                    result["reason"] = "research rule did not trigger"
        results.append(result)

    return {
        "schema_version": "1.0", "rule_version": RULE_VERSION, "as_of_local_date": as_of.isoformat(),
        "research_only": True,
        "disclaimer": "Exploratory personal trends only. No diagnosis, emergency detection, or treatment advice.",
        "settings": {"min_quality": MIN_QUALITY, "baseline_days": BASELINE_DAYS,
                     "recent_days": RECENT_DAYS, "min_baseline_days": MIN_BASELINE_DAYS,
                     "directed_z_gate": Z_GATE},
        "rejected": rejected, "results": results,
    }
