"""First-run synthetic report for agents; no HealthOS install, keys or network."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def readiness():
    try:
        ZoneInfo("UTC")
    except ZoneInfoNotFoundError:
        return {"status": "needs_timezone_data", "synthetic_only": True,
                "next_step": "Install the timezone dependency with python -m pip install tzdata, then retry. No account/key is needed."}
    return {"status": "ready", "synthetic_only": True, "network_required": False,
            "credentials_required": False, "python_package_install_required": False}


def start(workspace: Path):
    check = readiness()
    if check["status"] != "ready":
        raise RuntimeError(check["next_step"])
    workspace = workspace.expanduser().resolve()
    # A first-run example must never overwrite an existing personal workspace.
    workspace.mkdir(parents=True, exist_ok=False)
    from healthos.cli import demo
    from healthos.care import care_once
    from healthos.reports import agent_packet, build_report

    now = datetime(2026, 8, 1, 8, tzinfo=timezone.utc)
    metrics = ["sleep_minutes", "resting_heart_rate_bpm", "hrv_rmssd_ms"]
    profile = {"user_id": "demo-user", "timezone": "UTC", "goals": ["sleep", "recovery"],
               "main_concern": "Synthetic only: understand wearable sleep and recovery records.",
               "clarification_answers": {},
               "sources": [{"id": "synthetic", "adapter": "jsonl", "path": "synthetic_observations.jsonl"}],
               "consents": [{"source_id": "synthetic", "purpose": purpose, "metrics": metrics,
                             "granted": True, "granted_at": (now - timedelta(days=40)).isoformat()}
                            for purpose in ("local_analysis", "notifications")],
               "preferences": {"max_notices_per_7_days": 2}}
    demo(workspace)
    output = care_once(profile, workspace, date(2026, 7, 31), now, [])
    packet = agent_packet(profile, output, [])
    report = build_report(profile, output, [], now)
    for name, value in [("profile.synthetic.json", profile), ("agent-packet.json", packet),
                        ("wellness-report.json", report)]:
        (workspace / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (workspace / "wellness-report.md").write_text(report["markdown"], encoding="utf-8")
    receipt = {"status": "synthetic_report_ready", "synthetic_only": True,
               "analysis_date": report["as_of"], "generated_with": "production care_once / build_report",
               "workspace": str(workspace), "report": str(workspace / "wellness-report.md"),
               "report_json": str(workspace / "wellness-report.json"),
               "agent_packet": str(workspace / "agent-packet.json"),
               "metric_streams": len(report["metrics"]), "llm_called": False,
               "device_connected": False, "monitoring_started": False, "delivery_sent": False,
               "next_question": "Which wearable model do you own, and what one goal would you like to understand?",
               "next_guide": str(ROOT / "docs" / "agent-quickstart.md")}
    (workspace / "start-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the synthetic HealthOS first experience, not real monitoring")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="check readiness without creating files")
    mode.add_argument("--workspace", type=Path, help="new directory for synthetic results; existing directories are rejected")
    args = parser.parse_args(argv)
    try:
        result = readiness() if args.check else start(args.workspace)
    except (OSError, RuntimeError, ValueError) as exc:
        result = {"status": "blocked", "synthetic_only": True, "error": str(exc),
                  "fallback": "Read docs/sample-health-report.md; do not claim execution succeeded."}
    # ASCII JSON stays parseable across Windows console encodings; files remain UTF-8.
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["status"] in {"ready", "synthetic_report_ready"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
