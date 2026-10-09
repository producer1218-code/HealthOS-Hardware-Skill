"""Current synthetic private report workspace; no account or network calls."""
from datetime import datetime, timezone
import json
from pathlib import Path

from healthos.cli import care_demo
from healthos.journey import cycle
from healthos.monitor import write_json

workspace = Path("data/private/report-demo")
care_demo(workspace)
profile = json.loads((workspace / "care_profile.json").read_text(encoding="utf-8"))
profile["main_concern"] = "合成示例：希望理解 Fitbit 数据并改善作息。"
profile["clarification_answers"] = {"sleep": "合成背景：偶尔加班，希望行动足够小。"}
write_json(workspace / "profile.json", profile)
write_json(workspace / "report-settings.json", {"enabled": True, "interval_days": 7, "llm": {"provider": "none"}})
result = cycle(profile, workspace, datetime.now(timezone.utc))
report = result["periodic_report"].get("latest")
if report:
    print("Synthetic report:", workspace / "reports" / (report["id"] + ".md"))
print("healthos serve --workspace data/private/report-demo")
