"""Turn user goals and a named device into an honest measurement plan."""
from __future__ import annotations

from importlib.resources import files
import json

from healthos.planning import GOAL_METRICS, recommend


GOAL_GUIDANCE = {
    "sleep": {
        "questions": ["What would you like to improve: duration, timing, or daytime functioning?",
                      "Do shift work, travel, caregiving, or sleep disruptions affect the last month?"],
        "suggestion": "If your own sleep-duration trend shortens, check schedule and recording conditions. A consistent sleep/wake schedule is a general sleep habit, not a diagnosis or a guaranteed fix.",
        "source": "https://www.cdc.gov/sleep/about/index.html",
    },
    "recovery": {
        "questions": ["Are you trying to understand training recovery, fatigue, or another concern?",
                      "Have exercise, illness, travel, alcohol, medications, or device wear changed?"],
        "suggestion": "Review collection conditions and recent context before interpreting resting heart rate or HRV. HRV alone does not measure stress or recovery.",
        "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/",
    },
    "activity": {
        "questions": ["What kind of movement feels realistic and enjoyable for you?",
                      "Do work, mobility, caregiving, or access constraints affect activity?"],
        "suggestion": "Use step trends as a conversation starter. Step count alone does not establish activity intensity; WHO guidance says some activity is better than none.",
        "source": "https://www.who.int/publications/i/item/9789240014886",
    },
    "vitals": {
        "questions": ["Which vital sign are you concerned about, and what prompted that concern?",
                      "Was the device fitted and worn in its intended conditions?"],
        "suggestion": "Confirm the measurement method and device context. Consumer-wearable values should not be used alone to make a medical decision.",
        "source": "https://www.nature.com/articles/s41746-024-01151-3",
    },
    "wellbeing": {
        "questions": ["How would you describe your energy and wellbeing in your own words?",
                      "Would you prefer a voluntary weekly check-in rather than a daily sensor-based guess?"],
        "suggestion": "Use voluntary self-report for subjective wellbeing. A wearable cannot infer mood or psychological diagnosis from HRV.",
        "source": "https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01",
    },
    "social_connection": {
        "questions": ["Do you want to reflect on the quality of connection, opportunities to meet people, or both?",
                      "Would a private, optional check-in be useful?"],
        "suggestion": "Use voluntary self-report and context; do not infer loneliness from contacts, audio or wearable signals.",
        "source": "https://www.who.int/publications/i/item/978240112360",
    },
}

METRIC_GOAL = {
    "resting_heart_rate_bpm": "recovery", "hrv_rmssd_ms": "recovery", "hrv_sdnn_ms": "recovery",
    "sleep_minutes": "sleep", "steps_count": "activity", "self_report_energy_0_10": "wellbeing",
    "heart_rate_bpm": "vitals", "spo2_pct": "vitals", "respiratory_rate_bpm": "vitals",
    "skin_temp_c": "vitals",
}


def catalog() -> list[dict]:
    payload = json.loads(files("healthos").joinpath("device_catalog.json").read_text(encoding="utf-8"))
    return payload["models"]


def find_models(query: str = "") -> list[dict]:
    query = query.casefold().strip()
    return [item for item in catalog() if query in f"{item['vendor']} {item['model']} {item['id']}".casefold()]


def plan_for_user(profile: dict) -> dict:
    goals = profile.get("goals")
    if not isinstance(goals, list) or not goals or set(goals) - GOAL_METRICS.keys():
        raise ValueError("goals must be a nonempty list from the documented goal vocabulary")
    selected_id = profile.get("selected_model_id")
    selected = next((item for item in catalog() if item["id"] == selected_id), None) if selected_id else None
    if selected_id and selected is None:
        raise ValueError(f"unknown selected_model_id: {selected_id}")
    wanted = set().union(*(GOAL_METRICS[goal] for goal in goals))
    self_report = {metric for metric in wanted if metric.startswith("self_report_")}
    sensor_wanted = wanted - self_report
    readable = set(selected["readable_metrics_here"]) if selected else set()
    observed = sorted(wanted & readable)
    missing = sorted(wanted - readable)
    intent = str(profile.get("main_concern", ""))[:500]
    max_weekly = int(profile.get("max_notices_per_7_days", 2))
    if not 0 <= max_weekly <= 7:
        raise ValueError("max_notices_per_7_days must be between 0 and 7")
    status = ("self_report_first" if not sensor_wanted else
              "adapter_available_verify_access" if selected and observed else
              "needs_adapter_or_access" if selected else "choose_a_model")
    questions = [question for goal in goals for question in GOAL_GUIDANCE[goal]["questions"]]
    suggestions = [{"goal": goal, "text": GOAL_GUIDANCE[goal]["suggestion"],
                    "source": GOAL_GUIDANCE[goal]["source"],
                    "type": "general_wellness_not_individual_treatment"} for goal in goals]
    return {
        "schema_version": "1.0", "status": status, "user_intent_local_only": intent,
        "selected_model": selected, "goals": goals,
        "metrics_readable_here_for_goals": observed,
        "metrics_not_readable_here_for_goals": missing,
        "voluntary_self_report_metrics": sorted(self_report),
        "goal_details": [{"goal": goal, "wanted_metrics": sorted(GOAL_METRICS[goal]),
                          "readable_metrics": sorted(GOAL_METRICS[goal] & readable),
                          "not_available_here": sorted(GOAL_METRICS[goal] - readable)} for goal in goals],
        "questions_to_ask_user": questions,
        "general_suggestions": suggestions,
        "candidate_data_paths": recommend(goals) if sensor_wanted else [],
        "method": {"baseline_window_days": 28, "min_valid_baseline_days": 14,
                   "recent_window_days": 3, "per_device_baseline": True,
                   "change_detection": "median + MAD, metric direction and dual gates; thresholds unvalidated"},
        "notification_preference": {"max_notices_per_7_days": max_weekly},
        "next_step": ("Offer a voluntary check-in; no wearable measurement is required for this goal."
                      if status == "self_report_first" else
                      "Obtain a permitted export or saved API response and verify exact fields before running the monitor."
                      if status == "adapter_available_verify_access" else
                      "Confirm model-specific access or write an adapter; do not assume consumer features are API fields."
                      if selected else "Compare model rows and select a data path."),
        "clinical_status": "unvalidated_research; no diagnosis or treatment advice",
    }


def guidance_for_metric(metric: str) -> dict | None:
    goal = METRIC_GOAL.get(metric)
    if goal is None:
        return None
    item = GOAL_GUIDANCE[goal]
    return {"goal": goal, "questions": item["questions"],
            "suggested_next_step": item["suggestion"], "source": item["source"]}
