"""First-run behavior: isolated synthetic execution and no personal-data overwrite."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AgentStartTests(unittest.TestCase):
    def run_start(self, *args):
        return subprocess.run([sys.executable, "-I", str(ROOT / "scripts/agent_start.py"), *args],
                              cwd=ROOT.parent, capture_output=True, text=True, encoding="utf-8")

    def test_isolated_first_run_matches_packet_and_produces_real_report(self):
        with TemporaryDirectory() as directory:
            workspace = Path(directory) / "new"
            result = self.run_start("--workspace", str(workspace))
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            receipt = json.loads(result.stdout)
            report = json.loads(Path(receipt["report_json"]).read_text(encoding="utf-8"))
            packet = json.loads(Path(receipt["agent_packet"]).read_text(encoding="utf-8"))
            self.assertEqual(report["metrics"], packet["period_summary"])
            self.assertEqual(len(report["metrics"]), 3)
            self.assertEqual(report["as_of"], "2026-07-31")
            self.assertEqual(Path(receipt["report"]).read_text(encoding="utf-8"), report["markdown"])
            self.assertFalse(receipt["monitoring_started"])
            self.assertFalse(receipt["llm_called"])
            self.assertFalse(receipt["delivery_sent"])
            self.assertEqual(report["ai_status"], "disabled")
            self.assertEqual({row["device_id"] for row in report["metrics"]}, {"demo-device"})

    def test_existing_private_workspace_remains_untouched(self):
        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            record = workspace / "private.json"
            record.write_text("private sentinel", encoding="utf-8")
            result = self.run_start("--workspace", str(workspace))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["status"], "blocked")
            self.assertEqual(record.read_text(encoding="utf-8"), "private sentinel")
            self.assertEqual(list(workspace.iterdir()), [record])

    def test_check_does_not_create_first_run_files(self):
        result = self.run_start("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "ready")
