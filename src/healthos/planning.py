"""Transparent device selection from the interfaces this repository can use."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DevicePath:
    name: str
    adapter: str
    access: str
    metrics: tuple[str, ...]
    setup: str
    limitation: str


# These are data-access paths, not claims that every model measures every metric.
# Keep in sync with docs/device-matrix.md and verify exact device/app versions.
PATHS = (
    DevicePath("Fitbit / Google Health official export", "fitbit-takeout", "working_offline",
               ("resting_heart_rate_bpm", "hrv_rmssd_ms", "sleep_minutes", "steps_count"),
               "Download your official account export; select the ZIP or extracted directory.",
               "Observed export subsets only, no OAuth or live sync; separate device bindings; update snapshots."),
    DevicePath("Apple Health export", "apple-health-xml", "working_offline",
               ("resting_heart_rate_bpm", "heart_rate_bpm", "hrv_sdnn_ms", "spo2_pct", "skin_temp_c"),
               "Export Health data from the iPhone Health app, unzip, then use export.xml.",
               "Current adapter reads selected quantity records only; no sleep intervals or steps."),
    DevicePath("WHOOP v2 saved response", "whoop-v2-json", "working_offline",
               ("resting_heart_rate_bpm", "hrv_rmssd_ms", "sleep_minutes", "respiratory_rate_bpm"),
               "Obtain permitted WHOOP API access and save a tagged v2 recovery/sleep JSON response.",
               "This repository does not perform OAuth, paging, or live synchronization."),
    DevicePath("Any device with canonical CSV", "csv", "working_offline",
               ("resting_heart_rate_bpm", "heart_rate_bpm", "hrv_rmssd_ms", "hrv_sdnn_ms",
                "sleep_minutes", "steps_count", "spo2_pct", "skin_temp_c", "respiratory_rate_bpm",
                "self_report_energy_0_10"),
               "Map a lawful local export to the documented canonical CSV columns.",
               "Data quality and metric semantics depend on the user's mapping."),
    DevicePath("Android Health Connect", "custom", "integration_required",
               ("heart_rate_bpm", "sleep_minutes", "steps_count"),
               "Build an Android companion with per-type permissions and a canonical export adapter.",
               "No Android companion or Health Connect adapter is included."),
    DevicePath("Huawei / Xiaomi / Zepp / OPPO / vivo", "custom", "access_unverified",
               (), "Confirm exact model, region, account, SDK/API eligibility, and export rights first.",
               "No generic direct sensor access is claimed."),
)


GOAL_METRICS = {
    "recovery": {"resting_heart_rate_bpm", "hrv_rmssd_ms", "hrv_sdnn_ms"},
    "sleep": {"sleep_minutes"},
    "activity": {"steps_count"},
    "vitals": {"heart_rate_bpm", "spo2_pct", "respiratory_rate_bpm", "skin_temp_c"},
    "wellbeing": {"self_report_energy_0_10"},
    "social_connection": set(),  # not inferred from a wearable sensor
}


def recommend(goals: list[str], include_unbuilt: bool = False) -> list[dict]:
    unknown = set(goals) - GOAL_METRICS.keys()
    if unknown:
        raise ValueError(f"unknown goals: {', '.join(sorted(unknown))}")
    wanted = set().union(*(GOAL_METRICS[goal] for goal in goals)) if goals else set()
    choices = []
    for path in PATHS:
        if not include_unbuilt and path.access != "working_offline":
            continue
        matched = sorted(wanted.intersection(path.metrics))
        choices.append({
            "name": path.name, "adapter": path.adapter, "access": path.access,
            "matched_metrics": matched, "missing_metrics": sorted(wanted - set(path.metrics)),
            "match_count": len(matched), "setup": path.setup, "limitation": path.limitation,
        })
    # Generic CSV is an interoperability fallback, not evidence of a device's sensors.
    return sorted(choices, key=lambda item: (item["adapter"] == "csv", -item["match_count"], item["name"]))
