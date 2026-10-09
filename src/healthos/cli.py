"""Small offline CLI suitable for reproducing the examples."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import time
from pathlib import Path

from healthos.adapters import get_adapter
from healthos.analysis import analyze
from healthos.io import read_jsonl, write_jsonl
from healthos.model import METRICS, Observation
from healthos.planning import GOAL_METRICS, recommend
from healthos.monitor import monitor_once, read_config, read_state, write_json
from healthos.llm import narrate
from healthos.guide import find_models, plan_for_user
from healthos.permissions import connection_plan
from healthos.care import care_once
from healthos.outbox import Outbox
from healthos.onboarding import wizard
from zoneinfo import ZoneInfo
from dataclasses import replace


def demo(output_dir: Path) -> tuple[Path, Path]:
    """Write deterministic synthetic data, never real health records."""
    output_dir.mkdir(parents=True, exist_ok=True)
    observations = []
    start = date(2026, 7, 1)
    for index in range(31):
        day = start + timedelta(days=index)
        changed = index >= 28
        values = {
            "resting_heart_rate_bpm": 68 + (index % 2) if changed else 58 + (index % 3) - 1,
            "hrv_rmssd_ms": 32 + (index % 2) if changed else 43 + (index % 3) - 1,
            "sleep_minutes": 360 + 5 * (index % 2) if changed else 450 + 5 * (index % 3) - 5,
            "steps_count": 7900 + index * 10,
            "self_report_energy_0_10": 4 if changed else 7,
        }
        for metric, value in values.items():
            observations.append(Observation(
                "demo-user", datetime(day.year, day.month, day.day, 8, tzinfo=timezone.utc).isoformat(),
                metric, float(value), METRICS[metric][0], "synthetic-demo", "demo-device", 1.0,
                "synthetic data; no human participant",
            ))
    observations_file = output_dir / "synthetic_observations.jsonl"
    report_file = output_dir / "synthetic_report.json"
    write_jsonl(observations_file, observations)
    report_file.write_text(json.dumps(analyze(observations, date(2026, 7, 31)), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "monitor_config.json").write_text(json.dumps({
        "user_id": "demo-user", "goals": ["recovery", "sleep"],
        "source": {"adapter": "jsonl", "path": "synthetic_observations.jsonl"},
        "policy": {"plugin": "conservative", "cooldown_days": 7, "max_notices_per_7_days": 2},
        "llm": {"provider": "none"},
    }, indent=2) + "\n", encoding="utf-8")
    return observations_file, report_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="healthos", description="Offline, research-only personal trend prototype")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="normalize a local export to canonical JSONL")
    ingest.add_argument("--adapter", required=True, help="csv, apple-health-xml, whoop-v2-json, or module:Class")
    ingest.add_argument("--input", required=True, type=Path)
    ingest.add_argument("--user", required=True, help="local pseudonymous user ID")
    ingest.add_argument("--output", required=True, type=Path)
    run = sub.add_parser("analyze", help="generate an explainable JSON trend report")
    run.add_argument("--input", required=True, type=Path)
    run.add_argument("--as-of", required=True, type=date.fromisoformat, help="YYYY-MM-DD local date")
    run.add_argument("--output", required=True, type=Path)
    sample = sub.add_parser("demo", help="make deterministic, entirely synthetic example")
    sample.add_argument("--output-dir", default=Path("demo-output"), type=Path)
    sub.add_parser("adapters", help="list bundled adapters")
    sub.add_parser("plugins", help="list bundled adapters and user plugin drop-ins")
    devices = sub.add_parser("devices", help="compare usable data-access paths for goals")
    devices.add_argument("--goal", action="append", choices=sorted(GOAL_METRICS), default=[])
    devices.add_argument("--include-unbuilt", action="store_true")
    models = sub.add_parser("models", help="list named models with sensor, access and adapter boundaries")
    models.add_argument("--query", default="", help="vendor, model or id filter")
    plan = sub.add_parser("plan", help="turn a local user questionnaire into a measurement plan")
    plan.add_argument("--profile", required=True, type=Path)
    plan.add_argument("--output", required=True, type=Path)
    monitor = sub.add_parser("monitor", help="run one scheduled, stateful monitor pass")
    monitor.add_argument("--config", required=True, type=Path)
    monitor.add_argument("--as-of", type=date.fromisoformat,
                         help="YYYY-MM-DD; defaults to the computer's current local date")
    monitor.add_argument("--output", required=True, type=Path)
    monitor.add_argument("--state", required=True, type=Path)
    monitor.add_argument("--allow-cloud-health-data", action="store_true",
                         help="allow selected aggregate trend values to be sent to the configured HTTPS LLM")
    onboarding = sub.add_parser("onboard", help="guided, voluntary local data onboarding")
    onboarding.add_argument("--output", required=True, type=Path)
    connections = sub.add_parser("connection-plan", help="plan from goals and explicit source/purpose consent")
    connections.add_argument("--profile", required=True, type=Path)
    connections.add_argument("--output", required=True, type=Path)
    care = sub.add_parser("care", help="replan from consent, actual data and feedback; enqueue actions")
    care.add_argument("--profile", required=True, type=Path)
    care.add_argument("--as-of", type=date.fromisoformat, help="last completed local date; defaults to yesterday")
    care.add_argument("--state", required=True, type=Path, help="local SQLite outbox and feedback")
    care.add_argument("--output", required=True, type=Path)
    delivery = sub.add_parser("dispatch", help="deliver queued actions after rechecking consent and budget")
    delivery.add_argument("--profile", required=True, type=Path)
    delivery.add_argument("--state", required=True, type=Path)
    delivery.add_argument("--settings", type=Path, help="transport JSON; default local-json")
    delivery.add_argument("--output-dir", type=Path, default=Path("care-output/delivered"))
    delivery.add_argument("--allow-external-delivery", action="store_true")
    response = sub.add_parser("feedback", help="record execution or a separate self-reported outcome")
    response.add_argument("--profile", required=True, type=Path)
    response.add_argument("--state", required=True, type=Path)
    response.add_argument("--notice", required=True)
    response.add_argument("--status", required=True, choices=["executed", "skipped", "not_relevant", "felt_better", "unchanged", "felt_worse"])
    response.add_argument("--note", default="")
    forget = sub.add_parser("forget", help="delete this user's local outbox and feedback only")
    forget.add_argument("--profile", required=True, type=Path)
    forget.add_argument("--state", required=True, type=Path)
    care_sample = sub.add_parser("care-demo", help="synthetic consent → plan → actions → local delivery → feedback")
    care_sample.add_argument("--output-dir", type=Path, default=Path("care-output/demo"))
    start = sub.add_parser("start", help="goal-first guided onboarding for an existing Fitbit or other source")
    start.add_argument("--workspace", type=Path, default=Path("data/private/personal"))
    start.add_argument("--intent-settings", type=Path)
    start.add_argument("--allow-cloud-intent", action="store_true")
    web = sub.add_parser("serve", help="local interactive goals, consent, import, actions and feedback")
    web.add_argument("--workspace", type=Path, default=Path("data/private/personal"))
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--interval-minutes", type=int, default=60)
    web.add_argument("--intent-settings", type=Path)
    web.add_argument("--delivery-settings", type=Path)
    web.add_argument("--allow-external-delivery", action="store_true")
    watcher = sub.add_parser("watch", help="periodically replan from updated consented exports and dispatch")
    watcher.add_argument("--workspace", type=Path, default=Path("data/private/personal"))
    watcher.add_argument("--interval-minutes", type=int, default=60)
    watcher.add_argument("--once", action="store_true")
    watcher.add_argument("--delivery-settings", type=Path)
    watcher.add_argument("--allow-external-delivery", action="store_true")
    google = sub.add_parser("connect-google", help="guided user-started Google Health OAuth; eligible projects only")
    google.add_argument("--client", required=True, type=Path)
    google.add_argument("--connection", type=Path, default=Path("data/private/personal/google"))
    google.add_argument("--metric", action="append", required=True, choices=["resting_heart_rate_bpm", "hrv_rmssd_ms", "sleep_minutes"])
    google.add_argument("--port", type=int, default=8766)
    google.add_argument("--encrypted-storage-confirmed", action="store_true", help="confirm client, tokens and entire private workspace are on encrypted storage; HealthOS does not verify disk encryption")
    report_config = sub.add_parser("configure-reports", help="save explicit periodic-report and model settings")
    report_config.add_argument("--workspace", type=Path, default=Path("data/private/personal"))
    report_config.add_argument("--settings", required=True, type=Path)
    report_config.add_argument("--allow-cloud-report", action="store_true", help="allow deidentified metric aggregates to the configured model")
    report_run = sub.add_parser("report", help="generate one consent-aware report from the saved profile")
    report_run.add_argument("--workspace", type=Path, default=Path("data/private/personal"))
    memory_reset = sub.add_parser("forget-memory", help="clear local report history, answers and feedback; keep exports and goals")
    memory_reset.add_argument("--workspace", type=Path, default=Path("data/private/personal"))
    args = parser.parse_args(argv)
    if args.command == "connect-google":
        from healthos.google_health import authorize
        print("Google Health 新项目目前暂停接入；此连接器仅适用于已获准项目。浏览器将显示你选择的只读授权。")
        authorize(args.client, args.connection, args.metric, args.port, args.encrypted_storage_confirmed)
        print(f"连接已保存到 {args.connection}。在本地页面选择 Google Health API 和此目录，再确认指标与用途。")
    elif args.command == "configure-reports":
        settings = json.loads(args.settings.read_text(encoding="utf-8"))
        if not isinstance(settings.get("enabled", False), bool) or isinstance(settings.get("interval_days", 7), bool) or not isinstance(settings.get("interval_days", 7), int) or not 1 <= settings.get("interval_days", 7) <= 30:
            parser.error("报告间隔需为 1–30 天；enabled 必须为布尔值")
        llm = settings.setdefault("llm", {"provider": "none"})
        if "api_key" in llm:
            parser.error("密钥放环境变量，配置只填写 api_key_env")
        llm["share_aggregates"] = bool(args.allow_cloud_report)
        write_json(args.workspace / "report-settings.json", settings)
        print("已保存报告配置；报告仍需有效的指标分析与通知授权。模型发送聚合指标：" + str(llm["share_aggregates"]))
    elif args.command in {"report", "forget-memory"}:
        from healthos.reports import forget_memory, report_tick
        profile = json.loads((args.workspace / "profile.json").read_text(encoding="utf-8"))
        if args.command == "forget-memory":
            forget_memory(profile, args.workspace)
            print("已清除本地生成的报告、背景回答和反馈；原始导出、目标、连接和外部已发送副本需单独管理。")
        else:
            now = datetime.now(timezone.utc)
            as_of = now.astimezone(ZoneInfo(profile.get("timezone", "Asia/Shanghai"))).date() - timedelta(days=1)
            box = Outbox(args.workspace / "care.sqlite3")
            try:
                output = care_once(profile, args.workspace, as_of, now, box.feedback_for(profile["user_id"]))
                path = args.workspace / "report-settings.json"
                settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
                result = report_tick(profile, output, args.workspace, now, box, dict(settings, enabled=True), force=True)
                print(result["latest"]["markdown"] if "latest" in result else result["status"])
            finally:
                box.close()
    elif args.command in {"start", "serve", "watch"}:
        from healthos.journey import guided_start, readable_summary
        from healthos.server import serve, run_saved
        settings = json.loads(args.intent_settings.read_text(encoding="utf-8")) if getattr(args, "intent_settings", None) else None
        delivery = json.loads(args.delivery_settings.read_text(encoding="utf-8")) if getattr(args, "delivery_settings", None) else None
        if args.command == "start":
            output = guided_start(args.workspace, settings, args.allow_cloud_intent)
            return 2 if output["data_status"] == "source_error" else 0
        if args.interval_minutes < 1:
            parser.error("检查间隔至少 1 分钟")
        if args.command == "serve":
            serve(args.workspace, args.port, args.interval_minutes * 60, settings, delivery, args.allow_external_delivery)
        else:
            try:
                while True:
                    output = run_saved(args.workspace, delivery, args.allow_external_delivery)
                    print(readable_summary(output), flush=True)
                    if args.once:
                        return 2 if output["data_status"] == "source_error" else 0
                    time.sleep(args.interval_minutes * 60)
            except KeyboardInterrupt:
                return 0
    elif args.command == "onboard":
        write_json(args.output, wizard())
        print(f"wrote local profile to {args.output}")
    elif args.command == "care-demo":
        print(json.dumps(care_demo(args.output_dir), ensure_ascii=False, indent=2))
    elif args.command in {"connection-plan", "care", "dispatch", "feedback", "forget"}:
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc)
        if args.command == "connection-plan":
            write_json(args.output, connection_plan(profile, now))
        else:
            box = Outbox(args.state)
            try:
                if args.command == "care":
                    as_of = args.as_of or (now.astimezone(ZoneInfo(profile.get("timezone", "Asia/Shanghai"))).date() - timedelta(days=1))
                    output = care_once(profile, args.profile.parent, as_of, now, box.feedback_for(profile["user_id"]))
                    output["newly_enqueued"] = box.enqueue(output)
                    write_json(args.output, output)
                    print(f"wrote adaptive plan; queued {output['newly_enqueued']} candidates")
                elif args.command == "dispatch":
                    settings = json.loads(args.settings.read_text(encoding="utf-8")) if args.settings else {"plugin": "local-json", "output_dir": str(args.output_dir)}
                    print(json.dumps(box.dispatch(profile, now, settings, args.allow_external_delivery)))
                elif args.command == "feedback":
                    box.record_feedback(profile["user_id"], args.notice, args.status, now, args.note)
                    print("recorded voluntary feedback; next care pass will reconsider action suitability")
                else:
                    box.forget_user(profile["user_id"])
                    print("deleted local outbox and feedback; original exports and delivered copies are separate")
            finally:
                box.close()
    elif args.command == "ingest":
        count = write_jsonl(args.output, get_adapter(args.adapter).read(args.input, args.user))
        print(f"normalized {count} observations to {args.output}")
    elif args.command == "analyze":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report = analyze(list(read_jsonl(args.input)), args.as_of)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        print(f"wrote {len(report['results'])} metric streams to {args.output}")
    elif args.command == "demo":
        items = demo(args.output_dir)
        print("\n".join(str(item) for item in items))
        print(args.output_dir / "monitor_config.json")
    elif args.command == "devices":
        print(json.dumps(recommend(args.goal, args.include_unbuilt), indent=2, ensure_ascii=False))
    elif args.command == "models":
        print(json.dumps(find_models(args.query), indent=2, ensure_ascii=False))
    elif args.command == "plan":
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        write_json(args.output, plan_for_user(profile))
        print(f"wrote measurement plan to {args.output}")
    elif args.command == "monitor":
        config = read_config(args.config)
        output, state = monitor_once(config, args.config.parent, args.as_of or date.today(), read_state(args.state))
        for notice in output["notices"]:
            notice["narration"] = narrate(notice, config.get("llm", {}), args.allow_cloud_health_data)
        write_json(args.output, output)
        write_json(args.state, state)
        print(f"wrote {len(output['notices'])} new local notices to {args.output}")
    elif args.command == "plugins":
        from healthos.adapters import BUILTIN_ADAPTERS
        from healthos.plugins import DEFAULT_DIR, ENV_VAR, discover, plugin_dirs

        print(json.dumps({
            "bundled_adapters": sorted(BUILTIN_ADAPTERS),
            "custom_adapter_syntax": "module:Class",
            "drop_in_dir": str(DEFAULT_DIR),
            "env_var": ENV_VAR,
            "active_plugin_dirs": [str(path) for path in plugin_dirs()],
            "discovered_modules": discover(),
            "note": "Plugins are trusted Python, not a sandbox; inspect them before pointing them at real records.",
        }, indent=2, ensure_ascii=False))
    else:
        from healthos.adapters import BUILTIN_ADAPTERS

        print("\n".join((*BUILTIN_ADAPTERS, "module:Class custom adapter")))
    return 0


def care_demo(output_dir: Path) -> dict:
    """Fresh relative-date synthetic fixture; local delivery only, never personal data."""
    now = datetime.now(timezone.utc)
    as_of = now.astimezone(ZoneInfo("Asia/Shanghai")).date() - timedelta(days=1)
    observations_path, _ = demo(output_dir)
    shift = as_of - date(2026, 7, 31)
    observations = [replace(o, timestamp=(datetime.fromisoformat(o.timestamp) + shift).isoformat()) for o in read_jsonl(observations_path)]
    write_jsonl(observations_path, observations)
    metrics = ["sleep_minutes", "resting_heart_rate_bpm", "hrv_rmssd_ms"]
    profile = {"user_id": "demo-user", "timezone": "Asia/Shanghai", "goals": ["sleep", "recovery"],
               "sources": [{"id": "synthetic", "adapter": "jsonl", "path": observations_path.name}],
               "consents": [{"source_id": "synthetic", "purpose": purpose, "metrics": metrics,
                             "granted": True, "granted_at": (now - timedelta(days=40)).isoformat()}
                            for purpose in ("local_analysis", "notifications")],
               "preferences": {"max_notices_per_7_days": 2}}
    write_json(output_dir / "care_profile.json", profile)
    box = Outbox(output_dir / "care.sqlite3")
    try:
        output = care_once(profile, output_dir, as_of, now, box.feedback_for("demo-user"))
        output["newly_enqueued"] = box.enqueue(output)
        sent = box.dispatch(profile, now, {"plugin": "local-json", "output_dir": str(output_dir / "delivered")})
        first = box.db.execute("SELECT id FROM notices WHERE user_id='demo-user' AND status='sent' ORDER BY rowid LIMIT 1").fetchone()
        if first and not box.feedback_for("demo-user"):
            box.record_feedback("demo-user", first["id"], "executed", now, "synthetic feedback; no human participant")
        write_json(output_dir / "care_report.json", output)
        write_json(output_dir / "feedback.json", {"feedback": box.feedback_for("demo-user")})
        return {"synthetic_only": True, "as_of": as_of.isoformat(), "candidates": len(output["candidates"]),
                "newly_enqueued": output["newly_enqueued"], "delivery": sent, "report": str(output_dir / "care_report.json")}
    finally:
        box.close()
