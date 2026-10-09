"""Synthetic export and customer-journey regressions; no accounts or real records."""
from datetime import date, datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

from healthos.adapters.fitbit_takeout import FitbitTakeout
from healthos.intent import CompatibleAIIntent, propose_intent, validate_proposal
from healthos.journey import cycle, guided_start, make_profile
from healthos.outbox import Outbox
from healthos.server import make_server


NOW = datetime(2026, 10, 8, 2, tzinfo=timezone.utc)


def sleep_record(day="2026-10-07", minutes=420, log_id=1, main=True):
    return {"logId": log_id, "startTime": day + "T00:00:00", "endTime": day + "T08:00:00",
            "minutesAsleep": minutes, "mainSleep": main}


class FitbitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.reader = FitbitTakeout()
        self.reader.configure({"timezone": "Asia/Shanghai", "device_id": "synthetic-band"})

    def tearDown(self):
        self.temp.cleanup()

    def save(self, filename, content):
        path = self.root / filename
        path.write_text(content, encoding="utf-8")
        return path

    def test_directory_and_zip_preserve_methods_offsets_and_skip_apple(self):
        self.save("daily_resting_heart_rate.csv", "timestamp,beats per minute,data source\n2026-10-06T18:00:00Z,61,Google Health App\n2026-10-06T18:00:00Z,90,Apple Health Health Kit\n")
        self.save("daily_heart_rate_variability.csv", "timestamp,average heart rate variability milliseconds,data source\n2026-10-06T18:00:00Z,40,Google Health App\n2026-10-06T18:00:00Z,50,Apple Health Health Kit\n2026-10-06T19:00:00Z,nan,Google Health App\n")
        direct = list(self.reader.read(self.root, "synthetic-user"))
        self.assertEqual({o.metric for o in direct}, {"resting_heart_rate_bpm", "hrv_rmssd_ms"})
        self.assertTrue(all(o.timestamp.startswith("2026-10-07T02:") for o in direct))
        self.assertTrue(all(o.device_id == "synthetic-band" for o in direct))
        self.assertEqual(self.reader.diagnostics["skipped_non_fitbit_source"], 2)
        self.assertEqual(self.reader.diagnostics["invalid_rows"], 1)
        archive = self.root / "export.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for path in self.root.glob("*.csv"):
                z.write(path, "Takeout/Google Health/" + path.name)
        self.assertEqual(list(self.reader.read(archive, "synthetic-user")), direct)

    def test_consent_prevents_loading_unselected_export_files(self):
        self.save("sleep-2026-10-07.json", json.dumps([sleep_record()]))
        self.save("daily_resting_heart_rate.csv", "malformed,not,authorized")
        self.reader.configure({"allowed_metrics": ["sleep_minutes"]})
        self.assertEqual(len(list(self.reader.read(self.root, "u"))), 1)
        self.assertEqual(self.reader.diagnostics["recognized_files"], 1)

    def test_sleep_uses_longest_main_session_without_summing_naps(self):
        path = self.save("sleep-2026-10-07.json", json.dumps([sleep_record(), sleep_record(minutes=60, log_id=2, main=False)]))
        rows = list(self.reader.read(path, "u"))
        self.assertEqual([o.value for o in rows], [420])
        self.assertIn("longest_observed_session_per_wake_date", rows[0].context)
        self.assertGreater(self.reader.diagnostics["assumed_local_timezone"], 0)

    def test_sleep_csv_uses_last_revision_and_quarantines_equal_revision_conflicts(self):
        header = "sleep_id,minutes_asleep,sleep_start,sleep_end,sleep_last_updated,data_source,algorithm_version\n"
        row = "1,{minutes},2026-10-07T00:00:00Z,2026-10-07T08:00:00Z,2026-10-07T{hour}:00:00Z,DERIVED,1\n"
        path = self.save("UserSleeps_2026-10-07.csv", header + row.format(minutes=400, hour="09") + row.format(minutes=420, hour="10"))
        self.assertEqual([o.value for o in self.reader.read(path, "u")], [420])
        path.write_text(header + row.format(minutes=400, hour="09") + row.format(minutes=420, hour="09"))
        self.assertEqual(list(self.reader.read(path, "u")), [])

    def test_steps_deduplicate_intervals_and_exclude_conflicted_days(self):
        row = {"dateTime": "2026-10-07T10:00:00", "value": "10"}
        path = self.save("steps-2026-10-07.json", json.dumps([row, row, {"dateTime": "2026-10-07T10:01:00", "value": "20"}]))
        self.assertEqual([o.value for o in self.reader.read(path, "u")], [30])
        path.write_text(json.dumps([row, dict(row, value="11"), row]))
        self.assertEqual(list(self.reader.read(path, "u")), [])

    def test_conflicting_daily_rhr_is_not_guessed(self):
        path = self.save("daily_resting_heart_rate.csv", "timestamp,beats per minute,data source\n2026-10-07T00:00:00Z,60,Google Health App\n2026-10-07T00:00:00Z,70,Google Health App\n2026-10-07T00:00:00Z,60,Google Health App\n")
        self.assertEqual(list(self.reader.read(path, "u")), [])

    def test_legacy_step_timestamp_uses_export_month_day_year_and_user_timezone(self):
        path = self.save("steps-synthetic.json", json.dumps([
            {"dateTime": "10/07/26 10:00:00", "value": "10"},
            {"dateTime": "10/07/26 10:01:00", "value": "20"}]))
        rows = list(self.reader.read(path, "u"))
        self.assertEqual([o.value for o in rows], [30])
        self.assertTrue(rows[0].timestamp.startswith("2026-10-07"))
        self.assertEqual(self.reader.diagnostics["assumed_local_timezone"], 2)

    def test_unsafe_zip_and_file_limit_are_rejected_without_extraction(self):
        path = self.root / "bad.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("../sleep-2026-10-07.json", "[]")
        with self.assertRaises(ValueError):
            list(self.reader.read(path, "u"))
        self.assertEqual(len(list(self.root.iterdir())), 1)
        path = self.save("sleep-2026-10-07.json", "[]")
        with patch("healthos.adapters.fitbit_takeout.MAX_FILE_BYTES", 1), self.assertRaises(ValueError):
            list(self.reader.read(path, "u"))


class IntentTests(unittest.TestCase):
    def test_local_guidance_and_ai_permissions_are_explicit(self):
        output = propose_intent("我想改善睡眠和精力")
        self.assertEqual(output["goals"], ["sleep", "wellbeing"])
        self.assertEqual(output["method"], "local_keyword_guidance_not_ai")
        self.assertTrue(output["requires_confirmation"])
        with patch("healthos.intent.import_module") as loader, self.assertRaises(ValueError):
            propose_intent("sleep", {"provider": "untrusted:AI"})
        loader.assert_not_called()

    def test_ai_schema_strips_authorizations_and_rejects_unknown_goals(self):
        result = validate_proposal({"goals": ["sleep"], "questions": [], "consents": [True], "rules": {"threshold": 1}, "advice": "medicine"})
        self.assertNotIn("consents", result)
        self.assertNotIn("rules", result)
        self.assertNotIn("advice", result)
        with self.assertRaises(ValueError):
            validate_proposal({"goals": ["diagnose_arrhythmia"]})
        with self.assertRaises(ValueError):
            propose_intent("sleep", {"provider": "local", "api_key": "synthetic"})

    def test_optional_ai_sends_only_volunteered_text(self):
        response = io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"goals":["sleep"],"questions":[]}'}}]}).encode())
        settings = {"provider": "openai_compatible", "endpoint": "https://example.invalid/chat", "api_key_env": "SYNTHETIC_KEY", "model": "test"}
        with patch.dict("os.environ", {"SYNTHETIC_KEY": "dummy"}), patch("healthos.intent.build_opener") as opener:
            opener.return_value.open.return_value = response
            output = propose_intent("sleep better", settings, True)
        payload = json.loads(opener.return_value.open.call_args.args[0].data)
        self.assertEqual(payload["messages"][1], {"role": "user", "content": "sleep better"})
        self.assertTrue(output["requires_confirmation"])
        self.assertNotIn("observations", payload)


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.export = self.root / "sleep-2026-10-07.json"
        self.export.write_text(json.dumps([sleep_record()]))
        self.profile = make_profile("synthetic-user", "sleep better", ["sleep"], "fitbit-takeout", str(self.export), ["sleep_minutes"], True, True, now=NOW - timedelta(days=1))

    def tearDown(self):
        self.temp.cleanup()

    def test_goal_coaching_supports_calibration_and_repeat_delivery_deduplicates(self):
        first = cycle(self.profile, self.root, NOW)
        self.assertEqual(first["plan"]["runtime_goals"][0]["status"], "calibrating")
        self.assertEqual(first["recommendations"][0]["trigger"]["kind"], "user_requested_goal_coaching")
        self.assertNotIn("baseline_median", first["recommendations"][0]["observation"])
        self.assertEqual(first["delivery_result"]["sent"], 1)
        self.assertEqual(cycle(self.profile, self.root, NOW)["delivery_result"]["sent"], 0)
        self.assertTrue(first["recommendations"][0]["advice"]["evidence"])

    def test_feedback_pauses_same_action_without_claiming_causality(self):
        first = cycle(self.profile, self.root, NOW)
        box = Outbox(self.root / "care.sqlite3")
        try:
            box.record_feedback("synthetic-user", first["recommendations"][0]["id"], "felt_worse", NOW)
        finally:
            box.close()
        self.assertEqual(cycle(self.profile, self.root, NOW)["recommendations"], [])

    def test_no_data_stale_data_and_denied_notifications_do_not_push(self):
        self.profile["sources"][0]["path"] = ""
        self.assertEqual(cycle(self.profile, self.root, NOW)["recommendations"], [])
        self.profile["sources"][0]["path"] = str(self.export)
        self.export.write_text(json.dumps([sleep_record(day="2026-09-01")]))
        self.assertEqual(cycle(self.profile, self.root, NOW)["recommendations"], [])
        self.export.write_text(json.dumps([sleep_record()]))
        self.profile["consents"][1]["granted"] = False
        self.assertEqual(cycle(self.profile, self.root, NOW)["recommendations"], [])

    def test_bad_source_is_a_visible_failure_and_empty_path_is_pending(self):
        self.profile["sources"][0]["path"] = "missing.zip"
        output = cycle(self.profile, self.root, NOW)
        self.assertEqual(output["data_status"], "source_error")
        self.assertTrue(output["source_status"][0]["message"])
        self.profile["sources"][0]["path"] = ""
        self.assertEqual(cycle(self.profile, self.root, NOW)["source_status"][0]["status"], "waiting_for_export")

    def test_guide_recovers_from_invalid_menu_timezone_and_path(self):
        answers = iter(["sleep better", "banana", "1", "regular sleep", "Invalid/Zone", "", "0", "1", "/missing/synthetic", "", "1", "yes", "no", "no"])
        messages = []
        output = guided_start(self.root / "guided", ask=lambda prompt: next(answers), tell=messages.append)
        self.assertEqual(output["data_status"], "waiting_for_data")
        saved = json.loads((self.root / "guided/profile.json").read_text(encoding="utf-8"))
        self.assertEqual([g["granted"] for g in saved["consents"]], [True, False, False])
        self.assertTrue(any("时区无法" in message for message in messages))


class LocalServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.server = make_server(self.root, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, path, body, headers=None, raw=False):
        headers = {"X-HealthOS-Token": self.server.healthos_token, **(headers or {})}
        data = body if raw else json.dumps(body).encode()
        with urlopen(Request(self.url + path, data=data, headers=headers), timeout=5) as response:
            return json.load(response)

    def test_host_csrf_and_cross_origin_are_checked(self):
        with self.assertRaises(HTTPError) as error:
            self.post("/api/run", {}, {"X-HealthOS-Token": "wrong"})
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError):
            self.post("/api/intent", {"request": "sleep"}, {"Origin": "https://example.invalid"})
        with self.assertRaises(HTTPError):
            urlopen(Request(self.url + "/", headers={"Host": "evil.invalid"}), timeout=5)

    def test_upload_confirm_structured_action_feedback_revoke_and_multi_source(self):
        day = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        upload = self.post("/api/upload", json.dumps([sleep_record(day=day)]).encode(), {"X-Filename": "sleep-synthetic.json"}, raw=True)
        self.assertFalse((self.root / "profile.json").exists())
        body = {"confirmed": True, "user_id": "synthetic-user", "request": "我想改善睡眠", "goals": ["sleep"], "adapter": "fitbit-takeout", "file_id": upload["file_id"], "metrics": ["sleep_minutes"], "local_analysis": True, "notifications": True}
        output = self.post("/api/setup", body)
        self.assertEqual(output["delivery_result"]["sent"], 1)
        notice = output["recommendations"][0]
        self.assertEqual(notice["delivery_status"], "sent")
        with urlopen(self.url + "/api/latest", timeout=5) as response:
            self.assertEqual(json.load(response)["recommendations"][0]["id"], notice["id"])
        self.assertTrue(self.post("/api/feedback", {"notice_id": notice["id"], "status": "not_relevant"})["saved"])
        self.assertEqual(self.post("/api/run", {})["recommendations"], [])
        self.post("/api/setup", dict(body, add_source=True, device_id="second-band"))
        profile = json.loads((self.root / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(len(profile["sources"]), 2)
        self.assertEqual(len({s["id"] for s in profile["sources"]}), 2)
        remaining = self.post("/api/disconnect", {"source_id": profile["sources"][0]["id"]})
        self.assertEqual(len(remaining["source_status"]), 1)
        self.assertTrue(remaining["streams"])
        self.assertEqual(self.post("/api/revoke", {})["streams"], [])

    def test_periodic_report_configuration_memory_and_revocation_over_http(self):
        self.post("/api/report-settings", {"enabled": True, "interval_days": 7, "share_aggregates": False})
        day = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        upload = self.post("/api/upload", json.dumps([sleep_record(day=day)]).encode(), {"X-Filename": "sleep-synthetic.json"}, raw=True)
        output = self.post("/api/setup", {"confirmed": True, "user_id": "synthetic-user", "request": "sleep", "goals": ["sleep"],
                           "adapter": "fitbit-takeout", "file_id": upload["file_id"], "metrics": ["sleep_minutes"], "local_analysis": True, "notifications": True})
        self.assertEqual(output["periodic_report"]["status"], "sent")
        self.assertEqual(output["periodic_report"]["latest"]["metrics"][0]["missing_days"], 6)
        self.assertTrue((self.root / "memory.json").exists())
        self.assertEqual(self.post("/api/run", {})["periodic_report"]["status"], "waiting_for_next_period")
        self.assertTrue(self.post("/api/forget-memory", {})["saved"])
        self.assertFalse((self.root / "memory.json").exists())
        self.assertEqual(self.post("/api/revoke", {})["periodic_report"]["status"], "disabled_or_not_authorized")

    def test_setup_requires_confirmation_and_no_grants_are_inferred(self):
        with self.assertRaises(HTTPError):
            self.post("/api/setup", {"confirmed": False})
        output = self.post("/api/setup", {"confirmed": True, "request": "sleep", "goals": ["sleep"], "metrics": ["sleep_minutes"]})
        self.assertEqual(output["recommendations"], [])
        profile = json.loads((self.root / "profile.json").read_text(encoding="utf-8"))
        self.assertTrue(all(not g["granted"] for g in profile["consents"]))


if __name__ == "__main__":
    unittest.main()
