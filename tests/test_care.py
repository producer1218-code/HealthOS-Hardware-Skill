from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from healthos.adapters import get_adapter
from healthos.care import care_once, GuidelineAdvice
from healthos.cli import demo, main
from healthos.io import read_jsonl, write_jsonl
from healthos.outbox import Outbox, DeliveryUncertain
from healthos.permissions import collect, connection_plan
from healthos.feishu import FeishuDelivery
from healthos.onboarding import wizard


NOW = datetime(2026, 8, 1, 2, tzinfo=timezone.utc)
AS_OF = date(2026, 7, 31)


class BrokenTransport:
    external = False
    def send(self, notice, settings):
        raise RuntimeError("sensitive error text must not be stored")


class UncertainTransport:
    external = True
    def send(self, notice, settings):
        raise DeliveryUncertain("reconcile")


class CareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data, _ = demo(self.root)
        # A stronger synthetic HRV change exercises three candidates against a
        # two-notice budget without weakening the production research gate.
        write_jsonl(self.data, [replace(o, value=20) if o.metric == "hrv_rmssd_ms" and
                                date.fromisoformat(o.timestamp[:10]) >= date(2026, 7, 29) else o
                                for o in read_jsonl(self.data)])
        metrics = ["sleep_minutes", "resting_heart_rate_bpm", "hrv_rmssd_ms"]
        self.profile = {"user_id": "demo-user", "timezone": "Asia/Shanghai", "goals": ["sleep", "recovery"],
                        "sources": [{"id": "wearable", "adapter": "jsonl", "path": self.data.name}],
                        "consents": [{"source_id": "wearable", "purpose": p, "metrics": metrics,
                                      "granted": True, "granted_at": "2026-07-01T00:00:00+08:00"}
                                     for p in ("local_analysis", "notifications")],
                        "preferences": {"max_notices_per_7_days": 2}}
        self.box = Outbox(self.root / "state.sqlite3")
        self.settings = {"plugin": "local-json", "output_dir": str(self.root / "delivered")}

    def tearDown(self):
        self.box.close()
        self.temp.cleanup()

    def output(self):
        return care_once(self.profile, self.root, AS_OF, NOW, self.box.feedback_for("demo-user"))

    def test_refusal_prevents_reader_loading_and_keeps_other_goal_paths_optional(self):
        self.profile["consents"] = []
        with patch("healthos.permissions.get_adapter") as reader:
            output = self.output()
        reader.assert_not_called()
        self.assertEqual(output["candidates"], [])
        self.assertEqual(output["source_status"][0]["status"], "not_opened")
        self.assertTrue(all(g["status"] == "optional_connection_or_self_report" for g in output["plan"]["runtime_goals"]))

    def test_expired_or_future_consent_is_not_read(self):
        for grant in self.profile["consents"]:
            grant["expires_at"] = NOW.isoformat()
        with patch("healthos.permissions.get_adapter") as reader:
            self.output()
        reader.assert_not_called()
        for grant in self.profile["consents"]:
            grant.pop("expires_at")
            grant["granted_at"] = (NOW + timedelta(days=1)).isoformat()
        self.assertEqual(connection_plan(self.profile, NOW)["permitted_metrics"], [])

    def test_granted_subset_only_and_no_notice_without_notification_consent(self):
        self.profile["consents"][0]["metrics"] = ["sleep_minutes"]
        self.profile["consents"][1]["granted"] = False
        output = self.output()
        self.assertEqual({r["metric"] for r in output["report"]["results"]}, {"sleep_minutes"})
        self.assertEqual(output["candidates"], [])

    def test_dynamic_plan_accounts_for_stale_missing_records_and_source_failures(self):
        old = [replace(o, timestamp=(datetime.fromisoformat(o.timestamp) - timedelta(days=60)).isoformat()) for o in read_jsonl(self.data)]
        write_jsonl(self.data, old)
        output = self.output()
        self.assertEqual(output["report"]["results"], [])
        self.assertTrue(all(g["status"] == "data_incomplete" for g in output["plan"]["runtime_goals"]))
        self.assertEqual(output["streams"][0]["stale_days"], 60)
        self.profile["sources"][0]["path"] = "missing.jsonl"
        self.assertEqual(self.output()["source_status"][0]["status"], "source_error")

    def test_source_failure_does_not_block_other_source(self):
        second = deepcopy(self.profile["sources"][0]); second["id"] = "broken"; second["path"] = "missing"
        self.profile["sources"].append(second)
        grant = deepcopy(self.profile["consents"][0]); grant["source_id"] = "broken"
        self.profile["consents"].append(grant)
        output = self.output()
        self.assertTrue(output["candidates"])
        self.assertEqual(output["source_status"][1]["status"], "source_error")

    def test_wrong_user_never_reaches_analysis(self):
        write_jsonl(self.data, [replace(o, user_id="other-person") for o in read_jsonl(self.data)])
        output = self.output()
        self.assertEqual(output["report"]["results"], [])
        self.assertEqual(output["source_status"][0]["error_type"], "ValueError")

    def test_same_metric_different_sources_keeps_independent_baselines(self):
        other = self.root / "other.jsonl"
        write_jsonl(other, [replace(o, value=100 if o.metric == "resting_heart_rate_bpm" else o.value) for o in read_jsonl(self.data)])
        self.profile["sources"].append({"id": "second", "adapter": "jsonl", "path": other.name})
        grant = deepcopy(self.profile["consents"][0]); grant["source_id"] = "second"
        self.profile["consents"].append(grant)
        results = [r for r in self.output()["report"]["results"] if r["metric"] == "resting_heart_rate_bpm"]
        self.assertEqual(len(results), 2)
        self.assertEqual({r["status"] for r in results}, {"notable_change", "within_rule_limits"})

    def test_utc_records_are_bucketed_in_user_timezone_and_today_is_rejected(self):
        observation = next(read_jsonl(self.data))
        write_jsonl(self.data, [replace(observation, timestamp="2026-07-31T18:00:00+00:00")])
        observations, _ = collect(self.profile, self.root, NOW)
        self.assertTrue(observations[0].timestamp.startswith("2026-08-01T02:"))
        with self.assertRaises(ValueError):
            care_once(self.profile, self.root, date(2026, 8, 1), NOW)

    def test_connection_manifest_cannot_claim_unparsed_apple_sleep(self):
        self.profile["sources"][0].update(adapter="apple-health-xml", metrics=["sleep_minutes"])
        with self.assertRaises(ValueError):
            connection_plan(self.profile, NOW)

    def test_actions_have_evidence_and_respect_goal_priority_and_shift_work(self):
        output = self.output()
        self.assertEqual(output["candidates"][0]["metric"], "sleep_minutes")
        advice = output["candidates"][0]["advice"]
        self.assertEqual(advice["scope"], "general_wellness")
        self.assertIn("not_clinician_reviewed", advice["review_status"])
        self.assertTrue(advice["evidence"][0]["url"].startswith("https://"))
        self.profile["preferences"]["shift_work"] = True
        self.assertEqual(self.output()["candidates"][0]["advice"]["action_id"], "sleep-diary-v1")

    def test_guided_onboarding_requires_separate_explicit_permissions(self):
        answers = iter(["local-person", "Improve sleep", "1", "yes", "1", "my-export.jsonl", "1", "yes", "no", "no", "no"])
        profile = wizard(ask=lambda prompt: next(answers), tell=lambda message: None)
        self.assertEqual(profile["goals"], ["sleep"])
        self.assertEqual([g["granted"] for g in profile["consents"]], [True, False, False])
        self.assertEqual(profile["consents"][0]["metrics"], ["sleep_minutes"])

    def test_worse_self_report_pauses_action_without_changing_trend_rule(self):
        before = self.output()
        self.box.enqueue(before)
        self.box.dispatch(self.profile, NOW, self.settings)
        notice = self.box.db.execute("SELECT id FROM notices WHERE status='sent' ORDER BY rowid LIMIT 1").fetchone()[0]
        self.box.record_feedback("demo-user", notice, "felt_worse", NOW)
        after = self.output()
        self.assertEqual(before["report"], after["report"])
        self.assertNotIn("sleep_minutes", {n["metric"] for n in after["candidates"]})

    def test_invalid_advice_plugin_cannot_enqueue_clinical_action(self):
        with patch.object(GuidelineAdvice, "propose", return_value={"scope": "treatment"}):
            output = self.output()
        self.assertEqual(output["candidates"], [])
        self.assertTrue(output["plan"]["replan_reasons"]["suppressed_actions"])

    def test_pending_does_not_spend_budget_and_repeated_pass_deduplicates(self):
        output = self.output()
        self.assertEqual(self.box.enqueue(output), 3)
        self.assertEqual(self.box.enqueue(output), 0)
        self.assertEqual(self.box.db.execute("SELECT COUNT(*) FROM notices WHERE status='sent'").fetchone()[0], 0)
        self.assertEqual(self.box.dispatch(self.profile, NOW, self.settings)["sent"], 2)
        self.assertEqual(self.box.dispatch(self.profile, NOW, self.settings)["sent"], 0)

    def test_definitive_failure_retries_without_consuming_budget_or_storing_secret_error(self):
        self.box.enqueue(self.output())
        with patch("healthos.outbox.get_delivery", return_value=BrokenTransport()):
            result = self.box.dispatch(self.profile, NOW, self.settings)
        self.assertEqual(result["failed"], 3)
        self.assertEqual(result["sent"], 0)
        self.assertNotIn("sensitive", str(list(self.box.db.execute("SELECT error_type FROM notices"))))
        self.assertEqual(self.box.dispatch(self.profile, NOW, self.settings)["sent"], 2)

    def test_uncertain_remote_result_reserves_budget_and_is_not_retried(self):
        self.box.enqueue(self.output())
        grant = deepcopy(self.profile["consents"][0]); grant["purpose"] = "external_delivery"
        self.profile["consents"].append(grant)
        settings = {"plugin": "trusted:Transport", "recipient_user_id": "demo-user"}
        with patch("healthos.outbox.get_delivery", return_value=UncertainTransport()) as loader:
            result = self.box.dispatch(self.profile, NOW, settings, True)
            self.assertEqual(result["uncertain"], 2)
            self.assertEqual(self.box.dispatch(self.profile, NOW, settings, True)["uncertain"], 0)
            self.assertEqual(loader.call_count, 1)

    def test_revoked_permissions_cancel_queue_before_transport_loading(self):
        self.box.enqueue(self.output())
        self.profile["consents"][0]["revoked_at"] = NOW.isoformat()
        with patch("healthos.outbox.get_delivery") as transport:
            result = self.box.dispatch(self.profile, NOW, self.settings)
        transport.assert_not_called()
        self.assertEqual(result["cancelled"], 3)
        self.assertTrue(all(r[0] == "{}" for r in self.box.db.execute("SELECT payload FROM notices")))

    def test_removed_goal_cancels_its_pending_action(self):
        self.box.enqueue(self.output())
        self.profile["goals"] = ["recovery"]
        result = self.box.dispatch(self.profile, NOW, self.settings)
        self.assertEqual(result["cancelled"], 1)
        self.assertEqual(result["sent"], 2)

    def test_expired_notices_never_deliver_and_quiet_hours_defer(self):
        self.box.enqueue(self.output())
        self.profile["preferences"]["push_hours"] = [20]
        self.assertEqual(self.box.dispatch(self.profile, NOW, self.settings)["deferred"], 3)
        result = self.box.dispatch(self.profile, NOW + timedelta(days=3), self.settings)
        self.assertEqual(result["expired"], 3)
        self.assertFalse((self.root / "delivered").exists())

    def test_external_opt_in_requires_both_flag_and_scoped_consent(self):
        self.box.enqueue(self.output())
        settings = {"plugin": "trusted:Transport", "recipient_user_id": "demo-user"}
        with patch("healthos.outbox.get_delivery") as transport:
            self.assertEqual(self.box.dispatch(self.profile, NOW, settings)["deferred"], 3)
            self.assertEqual(self.box.dispatch(self.profile, NOW, settings, True)["deferred"], 3)
        transport.assert_not_called()

    def test_feedback_distinguishes_execution_from_outcome_and_user_rejection_replans(self):
        self.box.enqueue(self.output())
        self.box.dispatch(self.profile, NOW, self.settings)
        notice = self.box.db.execute("SELECT id FROM notices WHERE status='sent' ORDER BY rowid LIMIT 1").fetchone()[0]
        with self.assertRaises(ValueError):
            self.box.record_feedback("another-user", notice, "executed", NOW)
        self.box.record_feedback("demo-user", notice, "executed", NOW)
        self.box.record_feedback("demo-user", notice, "unchanged", NOW)
        self.box.record_feedback("demo-user", notice, "not_relevant", NOW)
        self.assertEqual({f["kind"] for f in self.box.feedback_for("demo-user")}, {"execution", "self_reported_outcome"})
        self.assertNotIn("sleep_minutes", {n["metric"] for n in self.output()["candidates"]})
        self.box.forget_user("demo-user")
        self.assertEqual(self.box.feedback_for("demo-user"), [])
        self.assertEqual(self.box.db.execute("SELECT COUNT(*) FROM notices").fetchone()[0], 0)

    def test_google_health_saved_rhr_preserves_methods_and_skips_unknown_sources(self):
        def point(platform, method):
            return {"dataSource": {"platform": platform, "device": {"displayName": "Synthetic Band"}},
                    "dailyRestingHeartRate": {"date": {"year": 2026, "month": 7, "day": 31}, "beatsPerMinute": "60",
                                              "dailyRestingHeartRateMetadata": {"calculationMethod": method}}}
        path = self.root / "rhr.json"
        path.write_text(json.dumps({"points": [point("FITBIT", "WITH_SLEEP"), point("FITBIT", "ONLY_WITH_AWAKE_DATA"), point("HEALTH_KIT", "WITH_SLEEP")]}))
        observations = list(get_adapter("google-health-rhr-json").read(path, "demo-user"))
        self.assertEqual(len(observations), 2)
        self.assertEqual(len({o.source for o in observations}), 2)
        self.assertTrue(all("civil-day anchor" in o.context for o in observations))

    def test_feishu_sends_only_aggregate_action_to_bound_user_with_stable_uuid(self):
        notice = self.output()["candidates"][0]
        settings = {"recipient_user_id": "demo-user", "receive_id": "synthetic-open-id"}
        with patch.dict("os.environ", {"HEALTHOS_FEISHU_APP_ID": "test-id", "HEALTHOS_FEISHU_APP_SECRET": "test-secret"}), \
             patch("healthos.feishu.post", side_effect=[{"tenant_access_token": "test-token"}, {"data": {"message_id": "message-1"}}]) as post:
            self.assertEqual(FeishuDelivery().send(notice, settings), "message-1")
        body = post.call_args_list[1].args[1]
        self.assertEqual(body["uuid"], notice["id"][:32])
        self.assertNotIn("demo-user", body["content"])
        self.assertNotIn("stream_key", body["content"])
        with self.assertRaises(ValueError):
            FeishuDelivery().send(notice, {"recipient_user_id": "another-user"})

    def test_complete_cli_demo_is_local_and_rerun_does_not_deliver_again(self):
        root = self.root / "care-demo"
        with patch("healthos.feishu.post") as network:
            self.assertEqual(main(["care-demo", "--output-dir", str(root)]), 0)
            self.assertEqual(main(["care-demo", "--output-dir", str(root)]), 0)
        network.assert_not_called()
        self.assertEqual(len(list((root / "delivered").glob("*.json"))), 2)
        self.assertTrue((root / "feedback.json").exists())


if __name__ == "__main__":
    unittest.main()
