"""A single private workspace for goal-driven onboarding, analysis and feedback."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from healthos.care import care_once
from healthos.intent import GOAL_LABELS, QUESTIONS, propose_intent
from healthos.monitor import write_json
from healthos.outbox import Outbox
from healthos.permissions import PATHS, validate_profile
from healthos.planning import GOAL_METRICS


METRIC_LABELS = {"sleep_minutes": "睡眠时长", "resting_heart_rate_bpm": "静息心率", "hrv_rmssd_ms": "睡眠 HRV（RMSSD）",
                 "hrv_sdnn_ms": "HRV（SDNN）", "steps_count": "步数", "heart_rate_bpm": "心率", "spo2_pct": "血氧",
                 "skin_temp_c": "皮温", "respiratory_rate_bpm": "呼吸频率", "self_report_energy_0_10": "自述精力"}
STATUS_LABELS = {"monitoring": "可以监控个人趋势", "calibrating": "正在建立个人基线", "data_incomplete": "数据不完整",
                 "waiting_for_data": "等待有效数据", "optional_connection_or_self_report": "该目标尚无可用数据，可调整授权或自愿记录"}


def make_profile(user_id: str, request: str, goals: list[str], adapter: str, path: str, metrics: list[str],
                 local_analysis: bool, notifications: bool, external_delivery: bool = False,
                 timezone_name: str = "Asia/Shanghai", answers: dict | None = None, now: datetime | None = None,
                 source_id: str = "personal-device", device_id: str = "user-declared-device-1") -> dict:
    now = now or datetime.now(timezone.utc)
    if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 100:
        raise ValueError("请填写 1–100 字的本地代号。")
    if not isinstance(request, str) or len(request) > 2000:
        raise ValueError("需求必须是最多 2000 字的文字。")
    if adapter not in PATHS:
        raise ValueError("请选择受支持的数据入口；自定义插件请使用高级配置。")
    if any(g not in GOAL_METRICS for g in goals) or not goals:
        raise ValueError("请先确认至少一个健康目标。")
    wanted = set().union(*(GOAL_METRICS[g] for g in goals))
    if set(metrics) - (PATHS[adapter][0] & wanted):
        raise ValueError("所选指标不能由当前入口用于这些目标。")
    if not isinstance(local_analysis, bool) or not isinstance(notifications, bool) or not isinstance(external_delivery, bool):
        raise ValueError("授权必须由用户明确选择。")
    if path.strip():
        path = str(Path(path.strip().strip('"').strip("'")).expanduser().resolve())
        if not Path(path).exists():
            raise ValueError("找不到所选路径，请重新选择文件；授权未保存。")
    profile = {"user_id": user_id, "timezone": timezone_name, "goals": list(dict.fromkeys(goals)),
               "main_concern": request[:2000], "clarification_answers": answers or {},
               "sources": [{"id": source_id, "adapter": adapter, "path": path, "device_id": device_id}],
               "consents": [{"source_id": source_id, "purpose": purpose, "metrics": metrics,
                             "granted": granted and bool(metrics), "granted_at": now.isoformat() if granted and metrics else None}
                            for purpose, granted in [("local_analysis", local_analysis), ("notifications", notifications), ("external_delivery", external_delivery)]],
               "preferences": {"max_notices_per_7_days": 2, "goal_coaching": True}, "advice_plugin": "guideline"}
    validate_profile(profile)
    return profile


def cycle(profile: dict, workspace: Path, now: datetime | None = None, delivery: dict | None = None, allow_external: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    workspace.mkdir(parents=True, exist_ok=True)
    as_of = now.astimezone(ZoneInfo(profile.get("timezone", "Asia/Shanghai"))).date() - timedelta(days=1)
    box = Outbox(workspace / "care.sqlite3")
    try:
        output = care_once(profile, workspace, as_of, now, box.feedback_for(profile["user_id"]))
        output["newly_enqueued"] = box.enqueue(output)
        output["delivery_result"] = box.dispatch(profile, now, delivery or {"plugin": "local-json", "output_dir": str(workspace / "delivered")}, allow_external)
        for notice in output["candidates"]:
            row = box.db.execute("SELECT status FROM notices WHERE id=? AND user_id=?", (notice["id"], profile["user_id"])).fetchone()
            notice["delivery_status"] = row["status"] if row else "not_queued"
        output["next_questions"] = [{"goal": goal, "question": QUESTIONS[goal]} for goal in profile["goals"]
                                    if not profile.get("clarification_answers", {}).get(goal)]
        # This is the one output consumers should render, independent of transport.
        output["recommendations"] = output["candidates"]
        output["data_status"] = "source_error" if any(s["status"] == "source_error" for s in output["source_status"]) else "available" if output["streams"] else "waiting_for_data"
        write_json(workspace / "latest.json", output)
        return output
    finally:
        box.close()


def readable_summary(output: dict) -> str:
    lines = ["你的健康计划"]
    for goal in output["plan"]["runtime_goals"]:
        lines.append(f"• {GOAL_LABELS[goal['goal']]}：{STATUS_LABELS[goal['status']]}")
    for source in output["source_status"]:
        if source.get("message"):
            lines.append(source["message"])
    for stream in output["streams"]:
        lines.append(f"{METRIC_LABELS.get(stream['metric'], stream['metric'])}：最新记录 {stream['latest_record_date']}；距分析日 {stream['stale_days']} 天")
    for notice in output.get("recommendations", output["candidates"]):
        lines.extend(["", "可以试试：" + notice["advice"]["action"], "依据：" + notice["advice"]["evidence"][0]["url"], "反馈标识：" + notice["id"]])
    if not output["candidates"]:
        lines.append("当前没有新的主动建议。请先查看数据覆盖与目标状态；这不表示健康已经达标。")
    return "\n".join(lines)


def guided_start(workspace: Path, settings: dict | None = None, allow_cloud: bool = False, ask=input, tell=print) -> dict:
    tell("欢迎使用 HealthOS。先了解你的目标，再决定哪些数据可以帮助你。")
    request = ask("你最想改善生活中的什么？例如睡眠规律、恢复或白天精力：")
    proposal = propose_intent(request, settings, allow_cloud)
    tell("建议关注：" + "、".join(GOAL_LABELS[g] for g in proposal["goals"]))
    options = list(GOAL_LABELS)
    tell(" / ".join(f"{i + 1} {GOAL_LABELS[g]}" for i, g in enumerate(options)))
    def choose(prompt, choices, default=None):
        while True:
            value = ask(prompt).strip()
            if not value and default is not None:
                return default
            try:
                numbers = [int(x.strip()) for x in value.split(",") if x.strip()]
                if not numbers or any(n < 1 or n > len(choices) for n in numbers):
                    raise ValueError()
                return list(dict.fromkeys(choices[n - 1] for n in numbers))
            except ValueError:
                tell("请填写上方编号，例如 1 或 1,2；没有保存任何授权。")
    goals = choose("确认目标编号，按重要程度排序（回车接受建议）：", options, proposal["goals"] or None)
    answers = {g: ask(QUESTIONS[g] + "（可跳过）：")[:500] for g in goals}
    while True:
        timezone_name = ask("你的时区（回车为 Asia/Shanghai）：").strip() or "Asia/Shanghai"
        try:
            ZoneInfo(timezone_name)
            break
        except (KeyError, ValueError):
            tell("时区无法识别，请使用 Asia/Shanghai 等 IANA 时区名称。")
    adapters = ["fitbit-takeout", "apple-health-xml", "jsonl", "csv"]
    tell("1 Fitbit/Google Health 官方导出 / 2 Apple 健康导出 / 3 已映射的 JSONL / 4 已映射的 CSV")
    adapter = choose("选择已有设备数据入口：", adapters)[0]
    for step in PATHS[adapter][1]:
        tell(step)
    while True:
        path = ask("导出 ZIP 或目录路径（没有文件可留空，之后补充）：")
        if not path.strip() or Path(path.strip().strip('\"').strip("'")).expanduser().exists():
            break
        tell("找不到路径，请重新填写或留空稍后补充；尚未保存授权。")
    wanted = set().union(*(GOAL_METRICS[g] for g in goals))
    metrics = sorted(PATHS[adapter][0] & wanted)
    tell("可选择：" + " / ".join(f"{i + 1} {METRIC_LABELS[m]}" for i, m in enumerate(metrics)))
    selected = choose("愿意开放哪些指标？编号用逗号分隔，留空表示不开放：", metrics, []) if metrics else []
    def consent(prompt):
        return bool(selected) and ask(prompt + " 输入 yes/是 才授权：").strip().lower() in {"yes", "是"}
    local = consent("允许在这台电脑分析这些数据？")
    notices = consent("允许主动生成并推送健康行动建议？")
    external = consent("允许提醒摘要发到你配置的飞书？飞书会收到健康摘要。")
    profile = make_profile("local-person", request, goals, adapter, path, selected, local, notices, external, timezone_name, answers)
    profile["intent_proposal"] = proposal
    workspace.mkdir(parents=True, exist_ok=True)
    write_json(workspace / "profile.json", profile)
    output = cycle(profile, workspace)
    tell(readable_summary(output))
    tell("档案和结构化建议已保存。运行 healthos serve 可在本地浏览器交互；watch 可持续检查更新的导出。")
    return output
