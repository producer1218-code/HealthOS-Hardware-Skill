"""Consent-aware adaptive care loop. Evidence informs actions, never diagnosis."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from zoneinfo import ZoneInfo

from healthos.analysis import analyze
from healthos.model import parse_timestamp
from healthos.model import METRICS
from healthos.permissions import collect, connection_plan, notification_allowed
from healthos.planning import GOAL_METRICS


class GuidelineAdvice:
    """Versioned general-wellness content. No claim of clinician review."""
    def propose(self, result: dict, profile: dict, feedback: list[dict]) -> dict:
        metric = result["metric"]
        preferences = profile.get("preferences", {})
        if metric == "sleep_minutes":
            shifted = preferences.get("shift_work", False)
            return {
                "action_id": "sleep-diary-v1" if shifted else "sleep-routine-v1",
                "action": "记录下一次主睡眠的开始、结束和醒后感受，找一个可行的规律。" if shifted else
                          "今晚选一个可行的睡前收尾时间，睡前半小时放下电子设备；明早记录感受。",
                "question": "最近的工作、照护、旅行或佩戴条件是否改变？这个动作适合你今晚的安排吗？",
                "evidence": [{"title": "CDC About Sleep", "url": "https://www.cdc.gov/sleep/about/index.html",
                              "supports": "一般睡眠习惯与睡眠日记；不支持此系统的触发阈值。"}],
                "success_check": "记录是否实际执行、可行性与次日自述感受；不将一次变化归因为建议。",
                "scope": "general_wellness", "content_version": "guideline-advice-v1",
                "review_status": "primary_source_based_not_clinician_reviewed",
            }
        if metric == "steps_count":
            return {"action_id": "activity-small-plan-v1", "action": "选一种你觉得可行的日常活动，为今天安排一个小目标，之后记录是否完成和感受。",
                    "question": "你有什么时间、环境或行动限制？什么活动能自然放进今天的生活？",
                    "evidence": [{"title": "WHO physical activity guidance", "url": "https://www.who.int/publications/i/item/9789240014886",
                                  "supports": "一般身体活动指导；步数不能证明中高强度活动达标，这个小目标的效果尚未验证。"}],
                    "success_check": "记录实际行动和可行性；不将步数上涨直接当健康改善。",
                    "scope": "general_wellness", "content_version": "guideline-advice-v2", "review_status": "primary_source_based_not_clinician_reviewed"}
        return {
            "action_id": "measurement-context-v1",
            "action": "先核对佩戴和记录条件，写下最近训练、旅行或作息是否改变；暂不判断原因。",
            "question": "这段记录能代表平时的你吗？你愿意补充哪些背景？",
            "evidence": [{"title": "HealthOS evidence-to-code ledger", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/",
                          "supports": "HRV 测量及情境解释原则；不支持诊断或此系统的精确阈值。"}]
                        if metric.startswith("hrv_") else
                        [{"title": "CDC sleep diary context", "url": "https://www.cdc.gov/sleep/about/index.html",
                          "supports": "记录睡眠、活动等背景；不证明静息心率或精力变化的原因。"}],
            "success_check": "背景是否补齐，记录条件是否可信；不自动改变医学判断。",
            "scope": "general_wellness", "content_version": "guideline-advice-v1",
            "review_status": "primary_source_based_not_clinician_reviewed",
        }


def get_advice(name: str):
    if name == "guideline":
        return GuidelineAdvice()
    if ":" not in name:
        raise ValueError("advice plugin requires module:Class")
    module, cls = name.split(":", 1)
    instance = getattr(import_module(module), cls)()
    if not callable(getattr(instance, "propose", None)):
        raise TypeError("advice plugin requires propose(result, profile, feedback)")
    return instance


def validate_advice(advice: dict) -> None:
    if advice.get("scope") != "general_wellness":
        raise ValueError("this workflow accepts general wellness actions only")
    for field in ("action_id", "action", "question", "success_check", "content_version", "review_status"):
        if not isinstance(advice.get(field), str) or not advice[field].strip():
            raise ValueError("advice missing required field")
    if not advice.get("evidence") or any(not item.get("url", "").startswith("https://")
                                         or not item.get("supports") for item in advice["evidence"]):
        raise ValueError("advice requires primary evidence and its support boundary")


def care_once(profile: dict, base_dir: Path, as_of: date, now: datetime,
              feedback: list[dict] | None = None) -> dict:
    timezone = ZoneInfo(profile.get("timezone", "Asia/Shanghai"))
    if now.tzinfo is None or as_of >= now.astimezone(timezone).date():
        raise ValueError("care requires a completed local date, not today or a future date")
    feedback = feedback or []
    plan = connection_plan(profile, now)
    observations, sources = collect(profile, base_dir, now)
    report = analyze(observations, as_of)
    latest = {}
    for observation in observations:
        day = parse_timestamp(observation.timestamp).date()
        if day <= as_of and observation.quality >= 0.8:
            key = (observation.source, observation.device_id, observation.metric)
            latest[key] = max(latest.get(key, day), day)
    # A stale stream may have no results at all in analyze's rolling window.
    streams = []
    for key, day in sorted(latest.items()):
        dates = {parse_timestamp(o.timestamp).date() for o in observations if
                 (o.source, o.device_id, o.metric) == key and o.quality >= 0.8 and parse_timestamp(o.timestamp).date() <= as_of}
        streams.append({"source": key[0], "device_id": key[1], "metric": key[2],
                        "latest_record_date": day.isoformat(), "first_record_date": min(dates).isoformat(),
                        "valid_record_days": len(dates), "stale_days": (as_of - day).days})
    runtime_goals = []
    for goal in profile["goals"]:
        results = [r for r in report["results"] if r["metric"] in GOAL_METRICS[goal]]
        usable = [r for r in results if r["status"] not in ("calibrating", "insufficient_recent_data")]
        related_streams = [s for s in streams if s["metric"] in GOAL_METRICS[goal]]
        if usable:
            state = "monitoring"
        elif results and all(r["status"] == "calibrating" for r in results):
            state = "calibrating"
        elif results or related_streams:
            state = "data_incomplete"
        elif not set(plan["permitted_metrics"]) & GOAL_METRICS[goal]:
            state = "optional_connection_or_self_report"
        else:
            state = "waiting_for_data"
        runtime_goals.append({"goal": goal, "status": state,
                              "usable_metrics": sorted({r["metric"] for r in usable}),
                              "missing_or_unusable_metrics": sorted(GOAL_METRICS[goal] - {r["metric"] for r in usable}),
                              "latest_streams": related_streams})
    candidates, suppressed = [], []
    def priority(result):
        return min((i for i, goal in enumerate(profile["goals"]) if result["metric"] in GOAL_METRICS[goal]), default=999)
    for result in sorted(report["results"], key=priority):
        if result["status"] != "notable_change":
            continue
        source_id = result["source"].split("::", 1)[0]
        if not notification_allowed(profile, source_id, result["metric"], now):
            continue
        try:
            advice = get_advice(profile.get("advice_plugin", "guideline")).propose(result, profile, feedback)
            validate_advice(advice)
        except Exception as exc:
            suppressed.append({"metric": result["metric"], "reason": "advice_plugin_error", "error_type": type(exc).__name__})
            continue
        refused = advice["action_id"] in profile.get("preferences", {}).get("disabled_actions", [])
        refused |= any(f.get("action_id") == advice["action_id"] and f.get("status") in {"not_relevant", "felt_worse"} for f in feedback)
        if refused:
            suppressed.append({"metric": result["metric"], "reason": "user_feedback_paused_action", "action_id": advice["action_id"]})
            continue
        stream_key = "|".join(result[k] for k in ("user_id", "source", "device_id", "metric"))
        stable = stream_key + "|" + as_of.isoformat() + "|" + result["rule_version"] + "|" + advice["content_version"]
        candidates.append({"id": sha256(stable.encode()).hexdigest(), "user_id": profile["user_id"],
                           "source_id": source_id, "metric": result["metric"], "stream_key": stream_key,
                           "as_of": as_of.isoformat(), "created_at": now.isoformat(),
                           "expires_at": datetime.combine(as_of + timedelta(days=2), datetime.min.time(), timezone).isoformat(),
                           "observation": {k: result[k] for k in ("metric", "unit", "baseline_median", "recent_median",
                                          "baseline_n_days", "recent_n_days", "baseline_window", "recent_window", "rule_version")},
                           "why_you": "同一来源、设备和方法下，最近三日相对个人基线持续变化；原因尚不确定。",
                           "advice": advice,
                           "feedback_options": ["executed", "skipped", "not_relevant"],
                           "outcome_options": ["felt_better", "unchanged", "felt_worse"],
                           "clinical_status": "unvalidated_research"})
        candidates[-1]["trigger"] = {"kind": "personal_trend", "validation": "engineering_hypothesis"}
        candidates[-1]["goal"] = next(g for g in profile["goals"] if result["metric"] in GOAL_METRICS[g])
    # Explicitly requested goal coaching is separate from change detection.
    # It may support the user during calibration but makes no physiological claim.
    if profile.get("preferences", {}).get("goal_coaching", False):
        for goal in profile["goals"]:
            if any(n.get("goal") == goal for n in candidates):
                continue
            eligible = [s for s in streams if s["metric"] in GOAL_METRICS[goal] and s["stale_days"] <= 2 and
                        notification_allowed(profile, s["source"].split("::", 1)[0], s["metric"], now)]
            if not eligible:
                continue
            stream = eligible[0]
            result = {"metric": stream["metric"], "status": "user_requested_goal_coaching"}
            try:
                advice = get_advice(profile.get("advice_plugin", "guideline")).propose(result, profile, feedback)
                validate_advice(advice)
            except Exception as exc:
                suppressed.append({"metric": stream["metric"], "reason": "advice_plugin_error", "error_type": type(exc).__name__})
                continue
            if advice["action_id"] in profile.get("preferences", {}).get("disabled_actions", []) or any(
                    f.get("action_id") == advice["action_id"] and f.get("status") in {"not_relevant", "felt_worse"} for f in feedback):
                continue
            source_id = stream["source"].split("::", 1)[0]
            key = f"{profile['user_id']}|{source_id}|goal-coaching|{goal}"
            week = as_of.isocalendar()
            identity = f"{key}|{week.year}-{week.week}|{advice['content_version']}"
            candidates.append({"id": sha256(identity.encode()).hexdigest(), "user_id": profile["user_id"], "source_id": source_id,
                               "metric": stream["metric"], "stream_key": key, "goal": goal, "as_of": as_of.isoformat(),
                               "created_at": now.isoformat(), "expires_at": datetime.combine(as_of + timedelta(days=2), datetime.min.time(), timezone).isoformat(),
                               "trigger": {"kind": "user_requested_goal_coaching", "validation": "general_wellness_not_anomaly"},
                               "observation": {"metric": stream["metric"], "unit": METRICS[stream["metric"]][0], "latest_record_date": stream["latest_record_date"],
                                               "valid_record_days": stream["valid_record_days"], "rule_version": "goal-coaching-v1"},
                               "why_you": "这是你确认的目标行动，已有相关记录；并非发现疾病或异常。个人变化基线仍按独立规则建立。",
                               "advice": advice, "feedback_options": ["executed", "skipped", "not_relevant"],
                               "outcome_options": ["felt_better", "unchanged", "felt_worse"], "clinical_status": "general_wellness"})
    plan["runtime_goals"] = runtime_goals
    plan["replan_reasons"] = {"permission_checked_at": now.isoformat(), "data_checked_as_of": as_of.isoformat(),
                              "feedback_count": len(feedback), "suppressed_actions": suppressed}
    return {"version": "care-v2", "user_id": profile["user_id"], "as_of": as_of.isoformat(),
            "plan": plan, "source_status": sources, "streams": streams,
            "report": report, "candidates": candidates, "delivery": "enqueue_separately"}
