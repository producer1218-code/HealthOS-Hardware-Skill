"""Voluntary, purpose-scoped consent and honest local data-path planning."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import re

from healthos.adapters import get_adapter
from healthos.model import METRICS, parse_timestamp
from healthos.planning import GOAL_METRICS


PATHS = {
    "fitbit-takeout": ({"resting_heart_rate_bpm", "hrv_rmssd_ms", "sleep_minutes", "steps_count"},
                       ["Google 账号：打开 https://takeout.google.com，选择 Google Health，申请导出并下载 ZIP。",
                        "原 Fitbit 登录：账号设置 → Data Export → Request Data，确认邮件后下载归档。",
                        "选择下载的 ZIP 或解压目录；不需要开发者账号或 API 密钥。导出是快照，持续监控需要更新文件。",
                        "仅读取已验证的字段子集；多台设备请分别导出/绑定，无法确认来源的 HRV 不混算。"]),
    "jsonl": (set(METRICS), ["选择本人合法取得的规范 JSONL 文件。", "逐项选择允许分析的指标；默认不开放。"]),
    "csv": (set(METRICS), ["将已有导出映射为规范 CSV，核对单位、来源、设备和时区。"]),
    "apple-health-xml": ({"heart_rate_bpm", "resting_heart_rate_bpm", "hrv_sdnn_ms", "spo2_pct", "skin_temp_c"},
                         ["iPhone 健康 App → 个人头像 → 导出所有健康数据。", "解压后选择 export.xml；当前读取器不处理睡眠和步数。"]),
    "whoop-v2-json": ({"resting_heart_rate_bpm", "hrv_rmssd_ms", "sleep_minutes", "respiratory_rate_bpm", "spo2_pct", "skin_temp_c"},
                      ["使用本人已获许可的 WHOOP API，将 recovery/sleep 响应分别保存为带 kind 的 JSON。", "当前不自动进行 OAuth 或同步。"]),
    "google-health-rhr-json": ({"resting_heart_rate_bpm"},
                             ["使用已有 Google Health 同步程序，选择本地 rhr.json。", "当前仅读取 Fitbit 静息心率，并按计算方法隔离；设备名称仅为临时标识。"]),
}
PURPOSES = {"local_analysis", "notifications", "external_delivery"}


def validate_profile(profile: dict) -> None:
    if not profile.get("user_id") or not isinstance(profile.get("goals"), list):
        raise ValueError("profile requires user_id and a goals list")
    if set(profile["goals"]) - GOAL_METRICS.keys():
        raise ValueError("unknown goal")
    ZoneInfo(profile.get("timezone", "Asia/Shanghai"))
    ids = set()
    for source in profile.get("sources", []):
        sid = source.get("id", "")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", sid) or sid in ids:
            raise ValueError("source IDs must be unique simple identifiers")
        ids.add(sid)
        adapter = source.get("adapter", "")
        if adapter not in PATHS and ":" not in adapter:
            raise ValueError("unknown adapter; custom adapters use module:Class")
        if "metrics" not in source and adapter not in PATHS:
            raise ValueError("custom source must declare metrics and setup_steps")
        metrics = set(source.get("metrics", PATHS.get(adapter, (set(), []))[0]))
        if metrics - METRICS.keys():
            raise ValueError("unsupported declared metric")
        if adapter in PATHS and metrics - PATHS[adapter][0]:
            raise ValueError("declared metrics exceed the working adapter")
    for grant in profile.get("consents", []):
        if grant.get("source_id") not in ids or grant.get("purpose") not in PURPOSES:
            raise ValueError("unknown consent source or purpose")
        if set(grant.get("metrics", [])) - METRICS.keys():
            raise ValueError("unknown consent metric")
        if not isinstance(grant.get("granted", False), bool):
            raise ValueError("granted must be an explicit boolean")
        if grant.get("granted") and not grant.get("granted_at"):
            raise ValueError("active consent requires granted_at")
        for key in ("granted_at", "expires_at", "revoked_at"):
            if grant.get(key):
                parse_timestamp(grant[key])
    budget = profile.get("preferences", {}).get("max_notices_per_7_days", 2)
    if isinstance(budget, bool) or not isinstance(budget, int) or not 0 <= budget <= 7:
        raise ValueError("notification budget must be an integer between 0 and 7")
    hours = profile.get("preferences", {}).get("push_hours")
    if hours is not None and (not isinstance(hours, list) or any(isinstance(h, bool) or not isinstance(h, int) or not 0 <= h <= 23 for h in hours)):
        raise ValueError("push_hours must be local hours between 0 and 23")


def permitted(profile: dict, source_id: str, purpose: str, now: datetime) -> set[str]:
    """Latest consent record for this source/purpose wins, including a refusal."""
    grants = [g for g in profile.get("consents", [])
              if g["source_id"] == source_id and g["purpose"] == purpose]
    if not grants:
        return set()
    grant = grants[-1]
    if not grant.get("granted") or grant.get("revoked_at"):
        return set()
    if parse_timestamp(grant["granted_at"]) > now:
        return set()
    if grant.get("expires_at") and parse_timestamp(grant["expires_at"]) <= now:
        return set()
    source = next((s for s in profile.get("sources", []) if s["id"] == source_id), None)
    if source is None:
        return set()
    supported = set(source.get("metrics", PATHS.get(source["adapter"], (set(), []))[0]))
    return set(grant.get("metrics", [])) & supported


def notification_allowed(profile: dict, source_id: str, metric: str, now: datetime, external: bool = False) -> bool:
    purposes = ["local_analysis", "notifications"] + (["external_delivery"] if external else [])
    wanted = set().union(*(GOAL_METRICS[g] for g in profile["goals"])) if profile["goals"] else set()
    return metric in wanted and all(metric in permitted(profile, source_id, purpose, now) for purpose in purposes)


def connection_plan(profile: dict, now: datetime) -> dict:
    validate_profile(profile)
    wanted = set().union(*(GOAL_METRICS[g] for g in profile["goals"])) if profile["goals"] else set()
    paths = []
    available = set()
    for source in profile.get("sources", []):
        if source["adapter"] in PATHS:
            supported, steps = PATHS[source["adapter"]]
        else:
            supported, steps = set(source["metrics"]), source.get("setup_steps", [])
        declared = set(source.get("metrics", supported))
        granted = permitted(profile, source["id"], "local_analysis", now) & wanted
        available |= granted
        paths.append({"source_id": source["id"], "adapter": source["adapter"],
                      "supported_metrics": sorted(declared), "permitted_goal_metrics": sorted(granted),
                      "optional_metrics_for_goals": sorted((declared & wanted) - granted),
                      "setup_steps": steps, "status": "permission_ready_verify_data" if granted else "not_opened",
                      "notification_metrics": sorted(permitted(profile, source["id"], "notifications", now) & granted)})
    return {"version": "consent-plan-v1", "goals": profile["goals"], "connections": paths,
            "permitted_metrics": sorted(available), "unavailable_goal_metrics": sorted(wanted - available),
            "principle": "拒绝开放不会阻止其他目标；授权不等于有数据，有数据不等于可下结论。",
            "fallback": "可以自愿记录睡眠日记或精力；不自动推断未开放的指标。",
            "permissions_are": "local processing/analysis permissions; vendor OAuth scopes must also be limited by a live connector"}


def collect(profile: dict, base_dir: Path, now: datetime) -> tuple[list, list]:
    """Never initialize or read a source unless relevant analysis was authorized.

    Local legacy export readers may parse a whole file; only consented, relevant
    records leave this boundary. Custom plugins are trusted code, not sandboxed.
    """
    validate_profile(profile)
    wanted = set().union(*(GOAL_METRICS[g] for g in profile["goals"])) if profile["goals"] else set()
    observations, status = [], []
    timezone = ZoneInfo(profile.get("timezone", "Asia/Shanghai"))
    for source in profile.get("sources", []):
        allowed = permitted(profile, source["id"], "local_analysis", now) & wanted
        if not allowed:
            status.append({"source_id": source["id"], "status": "not_opened", "count": 0})
            continue
        if not str(source.get("path", "")).strip():
            status.append({"source_id": source["id"], "status": "waiting_for_export", "count": 0,
                           "message": "还没有选择导出文件。先按接入计划下载数据，再选择 ZIP 或目录。"})
            continue
        try:
            path = Path(source["path"]).expanduser()
            if not path.is_absolute():
                path = base_dir / path
            adapter = get_adapter(source["adapter"])
            if callable(getattr(adapter, "configure", None)):
                adapter.configure({"timezone": profile.get("timezone", "Asia/Shanghai"),
                                   "device_id": source.get("device_id", source["id"]), "allowed_metrics": sorted(allowed)})
            batch = []
            for observation in adapter.read(path, profile["user_id"]):
                if observation.user_id != profile["user_id"]:
                    raise ValueError("user mismatch")
                if observation.metric not in allowed:
                    continue
                timestamp = parse_timestamp(observation.timestamp).astimezone(timezone).isoformat()
                batch.append(replace(observation, timestamp=timestamp,
                                     source=source["id"] + "::" + observation.source))
            observations.extend(batch)
            status.append({"source_id": source["id"], "status": "loaded" if batch else "no_permitted_records",
                           "count": len(batch), "observed_metrics": sorted({o.metric for o in batch}),
                           "diagnostics": getattr(adapter, "diagnostics", {})})
        except Exception as exc:
            # Keep one bad plugin from blocking other sources; no path/record/credential text in errors.
            hints = {"FileNotFoundError": "找不到文件，请重新选择导出 ZIP 或目录。",
                     "IsADirectoryError": "这个入口需要文件；Fitbit 导出目录请选择 Fitbit 导入器。",
                     "UnicodeDecodeError": "文件格式不匹配。压缩包请选择 Fitbit 导入器；其他文件请先核对格式。",
                     "JSONDecodeError": "文件不是可读取的 JSON，请核对导出格式。",
                     "ValueError": "字段、用户或格式不匹配，请查看接入说明；不会用不确定的数据给出结论。"}
            status.append({"source_id": source["id"], "status": "source_error", "error_type": type(exc).__name__, "count": 0,
                           "message": hints.get(type(exc).__name__, "接入失败，请检查该数据插件；其他已授权入口仍可使用。")})
    return observations, status
