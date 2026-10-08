from __future__ import annotations

from datetime import date
from pathlib import Path
import unittest

from healthos.cli import demo
from healthos.guide import catalog, find_models, plan_for_user
from healthos.monitor import monitor_once, read_config


class GuideTests(unittest.TestCase):
    def test_named_models_and_access_boundary(self):
        self.assertEqual(len(catalog()), 20)
        apple = find_models("watch series 12")[0]
        self.assertEqual(apple["adapter"], "apple-health-xml")
        self.assertNotIn("sleep_minutes", apple["readable_metrics_here"])
        fitbit = find_models("fitbit air")[0]
        self.assertEqual(fitbit["adapter"], "fitbit-takeout")
        self.assertIn("sleep_minutes", fitbit["readable_metrics_here"])
        self.assertIn("export", fitbit["adapter_limitation"])
        self.assertIn("no OAuth", fitbit["adapter_limitation"])

    def test_goal_plan_shows_missing_metric_and_questions(self):
        profile = {"goals": ["sleep", "recovery"], "selected_model_id": "apple-watch-series-12",
                   "main_concern": "Improve sleep", "max_notices_per_7_days": 1}
        plan = plan_for_user(profile)
        self.assertEqual(plan["status"], "adapter_available_verify_access")
        self.assertIn("sleep_minutes", plan["metrics_not_readable_here_for_goals"])
        self.assertIn("hrv_sdnn_ms", plan["metrics_readable_here_for_goals"])
        self.assertTrue(plan["questions_to_ask_user"])

    def test_social_goal_does_not_invent_sensor(self):
        plan = plan_for_user({"goals": ["social_connection"]})
        self.assertEqual(plan["status"], "self_report_first")
        self.assertEqual(plan["candidate_data_paths"], [])
        self.assertEqual(plan["metrics_readable_here_for_goals"], [])

    def test_notice_has_bounded_suggestion_and_source(self):
        root = Path(__file__).parent / "_work" / "guide"
        demo(root)
        config = read_config(root / "monitor_config.json")
        output, _ = monitor_once(config, root, date(2026, 7, 31))
        for notice in output["notices"]:
            self.assertTrue(notice["suggested_next_step"])
            self.assertTrue(notice["guidance_source"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
