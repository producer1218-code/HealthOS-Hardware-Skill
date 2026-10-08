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
    args = parser.parse_args(argv)
    if args.command in {"start", "serve", "watch"}:
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
    else:
        print("fitbit-takeout\ncsv\napple-health-xml\nwhoop-v2-json\njsonl\ngoogle-health-rhr-json\nmodule:Class custom adapter")
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
