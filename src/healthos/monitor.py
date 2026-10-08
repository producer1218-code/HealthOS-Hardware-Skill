"""One scheduled monitoring pass with replaceable policy and local state."""
from __future__ import annotations

from datetime import date, timedelta
from importlib import import_module
from pathlib import Path
import json
from typing import Protocol

from healthos.adapters import get_adapter
from healthos.analysis import analyze
from healthos.planning import GOAL_METRICS
from healthos.guide import guidance_for_metric


class NoticePolicy(Protocol):
    def select(self, report: dict, state: dict, as_of: date, settings: dict) -> list[dict]: ...


class ConservativePolicy:
    """One notice per stream per cooldown, with a global weekly budget."""

    def select(self, report: dict, state: dict, as_of: date, settings: dict) -> list[dict]:
        cooldown = int(settings.get("cooldown_days", 7))
        weekly_budget = int(settings.get("max_notices_per_7_days", 2))
        if cooldown < 1 or weekly_budget < 0:
            raise ValueError("invalid notification policy settings")
        last = state.setdefault("last_notice_by_stream", {})
        history = state.setdefault("notice_dates", [])
        recent_history = [date.fromisoformat(day) for day in history
                          if as_of - timedelta(days=6) <= date.fromisoformat(day) <= as_of]
        notices = []
        for result in report["results"]:
            if result["status"] != "notable_change":
                continue
            key = "|".join(str(result[field]) for field in ("user_id", "source", "device_id", "metric"))
            previous = date.fromisoformat(last[key]) if key in last else None
            if previous is not None and (as_of - previous).days < cooldown:
                continue
            if len(recent_history) + len(notices) >= weekly_budget:
                break
            guidance = guidance_for_metric(result["metric"])
            notices.append({
                "id": f"{key}|{as_of.isoformat()}", "date": as_of.isoformat(),
                "metric": result["metric"], "unit": result["unit"],
                "baseline_median": result["baseline_median"],
                "recent_median": result["recent_median"],
                "baseline_n_days": result["baseline_n_days"],
                "recent_n_days": result["recent_n_days"],
                "rule_version": result["rule_version"],
                "message": (f"A sustained personal change was observed in {result['metric']}: "
                            f"recent median {result['recent_median']:.1f} {result['unit']} versus "
                            f"baseline {result['baseline_median']:.1f} {result['unit']}. "
                            "Check fit, wear, travel, illness, and recording conditions. "
                            "This is not a diagnosis."),
                "questions": guidance["questions"] if guidance else ["Was the device worn as usual?"],
                "suggested_next_step": guidance["suggested_next_step"] if guidance else "Review the measurement context.",
                "guidance_source": guidance["source"] if guidance else None,
            })
            last[key] = as_of.isoformat()
        history.extend(notice["date"] for notice in notices)
        state["notice_dates"] = [day for day in history
                                 if date.fromisoformat(day) >= as_of - timedelta(days=6)]
        return notices


def get_policy(name: str) -> NoticePolicy:
    if name == "conservative":
        return ConservativePolicy()
    if ":" not in name:
        raise ValueError("policy must be 'conservative' or module:Class")
    module_name, class_name = name.split(":", 1)
    policy = getattr(import_module(module_name), class_name)()
    if not callable(getattr(policy, "select", None)):
        raise TypeError("policy must implement select(report, state, as_of, settings)")
    return policy


def read_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = ("user_id", "source", "goals")
    for field in required:
        if field not in config:
            raise ValueError(f"config missing {field}")
    if not isinstance(config["goals"], list) or set(config["goals"]) - GOAL_METRICS.keys():
        raise ValueError("goals must be a list from the documented goal vocabulary")
    source = config["source"]
    if not isinstance(source, dict) or not source.get("adapter") or not source.get("path"):
        raise ValueError("source requires adapter and path")
    llm = config.get("llm", {})
    if "api_key" in llm:
        raise ValueError("never store an API key in config; use api_key_env")
    return config


def monitor_once(config: dict, base_dir: Path, as_of: date, state: dict | None = None) -> tuple[dict, dict]:
    source = config["source"]
    source_path = Path(source["path"])
    if not source_path.is_absolute():
        source_path = base_dir / source_path
    observations = list(get_adapter(source["adapter"]).read(source_path, config["user_id"]))
    report = analyze(observations, as_of)
    allowed = set().union(*(GOAL_METRICS[goal] for goal in config["goals"])) if config["goals"] else set()
    report["results"] = [item for item in report["results"] if item["metric"] in allowed]
    new_state = json.loads(json.dumps(state or {}))
    policy_config = config.get("policy", {})
    policy = get_policy(policy_config.get("plugin", "conservative"))
    notices = policy.select(report, new_state, as_of, policy_config)
    return {"as_of": as_of.isoformat(), "goals": config["goals"],
            "report": report, "notices": notices,
            "delivery": "local_json_only", "clinical_status": "unvalidated_research"}, new_state


def read_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)
