from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from healthos.cli import demo
from healthos.llm import narrate
from healthos.monitor import monitor_once, read_config
from healthos.planning import recommend


class MonitorTests(unittest.TestCase):
    def test_demo_config_runs_once_and_deduplicates(self):
        # Existing demo fixture is synthetic; no personal export or network required.
        root = Path(__file__).parent / "_work" / "monitor"
        demo(root)
        config = read_config(root / "monitor_config.json")
        first, state = monitor_once(config, root, date(2026, 7, 31))
        second, _ = monitor_once(config, root, date(2026, 7, 31), state)
        self.assertGreater(len(first["notices"]), 0)
        self.assertEqual(second["notices"], [])
        self.assertTrue(all(item["rule_version"] for item in first["notices"]))

    def test_goals_filter_and_notification_budget(self):
        root = Path(__file__).parent / "_work" / "budget"
        demo(root)
        config = read_config(root / "monitor_config.json")
        config["goals"] = ["sleep"]
        config["policy"]["max_notices_per_7_days"] = 1
        output, _ = monitor_once(config, root, date(2026, 7, 31))
        self.assertEqual({item["metric"] for item in output["report"]["results"]}, {"sleep_minutes"})
        self.assertEqual(len(output["notices"]), 1)

    def test_key_must_stay_out_of_config_and_external_call_is_opt_in(self):
        root = Path(__file__).parent / "_work"
        config_path = root / "bad_config.json"
        config_path.write_text(json.dumps({"user_id": "u", "goals": ["sleep"],
            "source": {"adapter": "jsonl", "path": "x"},
            "llm": {"provider": "openai_compatible", "api_key": "never-store-me"}}), encoding="utf-8")
        with self.assertRaises(ValueError):
            read_config(config_path)
        with self.assertRaisesRegex(ValueError, "disabled"):
            narrate({"message": "local"}, {"provider": "openai_compatible"})

    def test_device_selection_distinguishes_mapped_csv(self):
        choices = recommend(["recovery", "sleep"])
        self.assertEqual(choices[0]["adapter"], "fitbit-takeout")
        self.assertEqual(choices[0]["matched_metrics"], ["hrv_rmssd_ms", "resting_heart_rate_bpm", "sleep_minutes"])
        self.assertEqual(choices[-1]["adapter"], "csv")
        self.assertNotIn("custom", {item["adapter"] for item in choices})

    def test_llm_receives_aggregates_without_identity_or_raw_records(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, limit):
                return b'{"choices":[{"message":{"content":"Plain trend summary"}}]}'

        class FakeOpener:
            def open(self, request, timeout):
                self.request = request
                return FakeResponse()

        opener = FakeOpener()
        notice = {"message": "local", "user_id": "private-person", "device_id": "private-watch",
                  "raw_records": ["private"], "metric": "sleep_minutes", "unit": "min",
                  "baseline_median": 450.0, "recent_median": 360.0,
                  "baseline_n_days": 28, "recent_n_days": 3, "rule_version": "research"}
        settings = {"provider": "openai_compatible", "endpoint": "https://example.com/v1/chat/completions",
                    "model": "test-model", "api_key_env": "TEST_HEALTHOS_KEY"}
        with patch.dict("os.environ", {"TEST_HEALTHOS_KEY": "test-only-key"}), \
             patch("healthos.llm.build_opener", return_value=opener):
            self.assertEqual(narrate(notice, settings, allow_cloud=True), "Plain trend summary")
        body = opener.request.data.decode("utf-8")
        self.assertNotIn("private-person", body)
        self.assertNotIn("private-watch", body)
        self.assertNotIn("raw_records", body)
        self.assertIn("sleep_minutes", body)


if __name__ == "__main__":
    unittest.main()
