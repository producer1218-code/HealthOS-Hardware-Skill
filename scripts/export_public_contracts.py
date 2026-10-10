"""Export public capabilities and paired synthetic agent/report examples, offline only."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from healthos.care import care_once
from healthos.cli import demo
from healthos.permissions import PATHS
from healthos.reports import agent_packet, build_report

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/producer1218-code/HealthOS-Hardware-Skill"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    conditions = {
        "google-health-api": "Experimental, eligible Google projects only; Fitbit origin; encrypted storage attestation; no real-account verification.",
        "google-health-json": "Authorized saved Google v4 dataPoints; Fitbit origin and processed main sleep only.",
        "fitbit-takeout": "Observed official export subsets; manual refresh; not every device/export version verified.",
        "apple-health-xml": "Partial export reader; no sleep duration or steps; SDNN is not RMSSD.",
        "whoop-v2-json": "Already authorized saved responses; no online WHOOP OAuth.",
        "google-health-rhr-json": "Legacy saved Fitbit-origin RHR subset; calculation methods stay separate.",
        "csv": "Operator-mapped canonical fields; no device compatibility implied.",
        "jsonl": "Canonical records; no device compatibility implied.",
    }
    save(ROOT / "healthos-skill.json", {
        "manifest_version": "healthos-skill-v1", "name": "HealthOS Hardware Skill", "skill_name": "healthos",
        "aliases": ["HealthOS Open", "HealthOS Skill", "healthos-open"], "version": "0.6.0.dev0", "reviewed_date": "2026-10-10",
        "canonical_repository": REPO, "license": "MIT",
        "summary": "A methodology for your existing agent: discover wearable data access, clarify personal health questions, design observation plans and review evidence-linked reports and feedback.",
        "entrypoints": {"first_run": "START_HERE.md", "first_run_contract": "agent-start.json",
                        "skill": "skills/healthos/SKILL.md", "user": "docs/start-here.md",
                        "observation_method": "skills/healthos/references/observation-method.md",
                        "observation_plan": "skills/healthos/references/observation-plan-v1.json",
                        "methods": "docs/report-methodology.md", "faq": "docs/faq.md",
                        "deployment": "docs/install.md", "schema": "schemas/agent-context-v1.schema.json",
                        "synthetic_input": "examples/agent_packet.synthetic.json",
                        "synthetic_output": "examples/wellness_report.synthetic.json"},
        "data_adapters": [{"id": name, "metrics": sorted(fields), "conditions": conditions[name]}
                          for name, (fields, _) in PATHS.items()],
        "unsupported_dedicated_adapters": ["Huawei", "Xiaomi", "Amazfit/Zepp", "OPPO", "vivo"],
        "report": {"input_version": "agent-context-v1", "output_version": "wellness-report-v1",
                   "summary_window_completed_days": 7, "ui_delivery_cadence_days": [7, 14, 30],
                   "execution": "Requires an operator-run process; the skill is not a scheduler."},
        "llm": {"required": False, "bundled_interface": "Chat Completions JSON",
                "plugin_interface": "render(aggregate_packet, settings)", "external_share_default": False,
                "cloud_input_version": "report-aggregate-v1", "credentials": "Operator environment variable, never a public file."},
        "interfaces": ["CLI", "trusted Python plugins", "local report JSON", "Agent Skills instructions"],
        "mcp_server": False, "pages_live_verified": False, "clinical_validation": False,
        "validation_limits": ["Synthetic tests and mocked APIs", "No real Fitbit Air account verification",
                              "No cross-host skill behavioral verification", "No clinician sign-off or clinical benefit study"],
        "privacy": "Full local packets may contain identifiers and user context; external sharing requires separate consent.",
    })
    with TemporaryDirectory(prefix="healthos-public-") as directory:
        work = Path(directory)
        demo(work)
        now = datetime(2026, 8, 1, 8, tzinfo=timezone.utc)
        metrics = ["sleep_minutes", "resting_heart_rate_bpm", "hrv_rmssd_ms"]
        profile = {"user_id": "demo-user", "timezone": "Asia/Shanghai", "goals": ["sleep", "recovery"],
                   "main_concern": "Synthetic only: understand wearable sleep and recovery records.",
                   "clarification_answers": {"sleep": "Synthetic context: occasional late work; prefer a small action."},
                   "sources": [{"id": "synthetic", "adapter": "jsonl", "path": "synthetic_observations.jsonl"}],
                   "consents": [{"source_id": "synthetic", "purpose": purpose, "metrics": metrics,
                                 "granted": True, "granted_at": (now-timedelta(days=40)).isoformat()}
                                for purpose in ("local_analysis", "notifications")],
                   "preferences": {"max_notices_per_7_days": 2}}
        output = care_once(profile, work, date(2026, 7, 31), now, [])
        save(ROOT / "examples/agent_packet.synthetic.json", agent_packet(profile, output, []))
        save(ROOT / "examples/wellness_report.synthetic.json", build_report(profile, output, [], now))
    print("Exported capabilities and paired synthetic examples; no real account or network call.")


if __name__ == "__main__":
    main()
