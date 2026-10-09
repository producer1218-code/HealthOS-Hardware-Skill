"""Synthetic end-to-end reports and mocked Google reads; no account credentials."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from healthos.care import care_once
from healthos.cli import demo
from healthos.google_health import GoogleHealthAPI, GoogleHealthSnapshot, authorize, fetch_points, scopes_for
from healthos.journey import cycle, make_profile
from healthos.monitor import write_json
from healthos.outbox import Outbox, DeliveryUncertain
from healthos.permissions import collect
from healthos.reports import agent_packet, build_report, cloud_packet, forget_memory, render_ai, report_tick

NOW = datetime(2026, 8, 1, 8, tzinfo=timezone.utc)
AS_OF = date(2026, 7, 31)


def point(metric="rhr", value=60, day=31, device="Synthetic Air", method="WITH_SLEEP"):
    result = {"dataSource": {"platform": "FITBIT", "device": {"displayName": device}, "recordingMethod": "DERIVED"}}
    d = {"year": 2026, "month": 7, "day": day}
    if metric == "rhr":
        result["dailyRestingHeartRate"] = {"date": d, "beatsPerMinute": str(value), "dailyRestingHeartRateMetadata": {"calculationMethod": method}}
    elif metric == "hrv":
        result["dailyHeartRateVariability"] = {"date": d, "averageHeartRateVariabilityMilliseconds": value}
    else:
        result["sleep"] = {"interval": {"endTime": f"2026-07-{day:02d}T00:00:00Z"},
                           "metadata": {"processed": True, "mainSleep": True}, "summary": {"minutesAsleep": str(value)}}
    return result


class GoogleTests(unittest.TestCase):
    def parser(self, points, metrics=None):
        reader = GoogleHealthSnapshot()
        reader.configure({"timezone": "Asia/Shanghai", "allowed_metrics": metrics or ["resting_heart_rate_bpm", "hrv_rmssd_ms", "sleep_minutes"]})
        return list(reader.parse({"dataPoints": points}, "synthetic")), reader.diagnostics

    def test_daily_metrics_and_processed_main_sleep(self):
        data, _ = self.parser([point(), point("hrv", 42), point("sleep", 450)])
        self.assertEqual({o.metric for o in data}, {"resting_heart_rate_bpm", "hrv_rmssd_ms", "sleep_minutes"})
        self.assertTrue(all(o.timestamp.endswith("+08:00") for o in data))

    def test_scope_minimization_and_unsupported_types(self):
        self.assertEqual(len(scopes_for(["resting_heart_rate_bpm", "hrv_rmssd_ms"])), 1)
        self.assertTrue(scopes_for(["sleep_minutes"])[0].endswith("sleep.readonly"))
        with self.assertRaises(ValueError):
            scopes_for(["steps_count"])

    def test_conflicts_duplicates_methods_and_devices_are_separate(self):
        data, diag = self.parser([point(), point(), point(value=61), point(method="ONLY_WITH_AWAKE_DATA"), point(device="Other synthetic")])
        self.assertEqual(len(data), 2)
        self.assertGreater(diag["invalid_records"], 0)
        self.assertEqual(len({o.device_id for o in data}), 2)

    def test_unknown_origin_rmssd_variant_and_unprocessed_sleep_are_not_used(self):
        apple = point(); apple["dataSource"]["platform"] = "HEALTH_CONNECT"
        deep = point("hrv"); deep["dailyHeartRateVariability"].pop("averageHeartRateVariabilityMilliseconds")
        deep["dailyHeartRateVariability"]["deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds"] = 50
        sleep = point("sleep", 450); sleep["sleep"]["metadata"]["processed"] = False
        self.assertEqual(self.parser([apple, deep, sleep])[0], [])

    def test_metrics_filter_prevents_unselected_observations(self):
        data, _ = self.parser([point(), point("hrv", 42), point("sleep", 450)], ["sleep_minutes"])
        self.assertEqual([o.metric for o in data], ["sleep_minutes"])

    def test_documented_main_alias_and_conflicting_metadata(self):
        item = point("sleep", 400)
        item["sleep"]["metadata"]["main"] = item["sleep"]["metadata"].pop("mainSleep")
        self.assertEqual(len(self.parser([item])[0]), 1)
        item["sleep"]["metadata"]["mainSleep"] = False
        self.assertEqual(self.parser([item])[0], [])

    def test_pagination_endpoint_sleep_end_filter_and_source_family(self):
        responses = [SimpleNamespace(status_code=200, content=b"{}", json=lambda: {"dataPoints": [point()], "nextPageToken": "synthetic-next"}),
                     SimpleNamespace(status_code=200, content=b"{}", json=lambda: {"dataPoints": [point("sleep", 450)]})]
        calls = []
        def get(url, **kwargs):
            calls.append((url, deepcopy(kwargs)))
            return responses.pop(0)
        payload = fetch_points(SimpleNamespace(get=get), ["sleep_minutes"], date(2026, 7, 25), AS_OF, "Asia/Shanghai")
        self.assertEqual(len(payload["dataPoints"]), 2)
        self.assertIn("sleep.interval.end_time", calls[0][1]["params"]["filter"])
        self.assertEqual(calls[1][1]["params"]["pageToken"], "synthetic-next")
        self.assertEqual(calls[0][1]["params"]["dataSourceFamily"], "users/me/dataSourceFamilies/google-wearables")
        self.assertFalse(calls[0][1]["allow_redirects"])

    def test_repeated_token_and_api_failures_do_not_return_partial_data(self):
        session = SimpleNamespace(get=lambda *a, **kw: SimpleNamespace(status_code=200, content=b"{}", json=lambda: {"dataPoints": [], "nextPageToken": "repeat"}))
        with self.assertRaises(ValueError):
            fetch_points(session, ["sleep_minutes"], AS_OF, AS_OF, "Asia/Shanghai")

    def test_google_requires_explicit_encrypted_storage_before_oauth(self):
        with self.assertRaises(ValueError):
            authorize(Path("not-read"), Path("not-written"), ["sleep_minutes"])


@unittest.skipUnless(importlib.util.find_spec("google_auth_oauthlib"), "optional Google libraries not installed")
class OfficialOAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.client = self.root / "client.secrets.json"
        write_json(self.client, {"web": {"client_id": "synthetic.apps.googleusercontent.com", "client_secret": "synthetic-only",
                                       "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}})
        self.scopes = scopes_for(["sleep_minutes"])
        self.token = {"token": "SYNTHETIC_NOT_REAL", "refresh_token": "SYNTHETIC_NOT_REAL", "scopes": self.scopes,
                      "token_uri": "https://oauth2.googleapis.com/token", "client_id": "synthetic", "client_secret": "synthetic-only"}
        self.credentials = SimpleNamespace(refresh_token="SYNTHETIC_NOT_REAL", granted_scopes=self.scopes,
                                           scopes=self.scopes, to_json=lambda: json.dumps(self.token))

    def tearDown(self):
        # Windows chmod(600) remains writable, no real credentials are involved.
        self.temp.cleanup()

    def test_success_verifies_identity_and_saves_connection_after_browser_flow(self):
        with patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_config") as factory, patch("google.auth.transport.requests.AuthorizedSession") as session:
            factory.return_value.run_local_server.return_value = self.credentials
            session.return_value.__enter__.return_value.get.return_value.status_code = 200
            authorize(self.client, self.root / "google", ["sleep_minutes"], encrypted_storage_confirmed=True)
            self.assertTrue((self.root / "google/oauth.json").exists())
            self.assertTrue(json.loads((self.root / "google/connection.json").read_text())["encrypted_storage_confirmed"])
            self.assertTrue(factory.call_args.kwargs["autogenerate_code_verifier"])
            self.assertEqual(factory.return_value.run_local_server.call_args.kwargs["host"], "127.0.0.1")

    def test_unlinked_or_ineligible_account_never_persists_credentials(self):
        with patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_config") as factory, patch("google.auth.transport.requests.AuthorizedSession") as session:
            factory.return_value.run_local_server.return_value = self.credentials
            session.return_value.__enter__.return_value.get.return_value.status_code = 400
            with self.assertRaises(ValueError):
                authorize(self.client, self.root / "google", ["sleep_minutes"], encrypted_storage_confirmed=True)
            self.assertFalse((self.root / "google/oauth.json").exists())

    def test_live_reader_requests_only_locally_permitted_types_and_refreshes_token(self):
        connection = self.root / "google"
        connection.mkdir()
        write_json(connection / "connection.json", {"metrics": ["sleep_minutes", "resting_heart_rate_bpm"], "encrypted_storage_confirmed": True})
        write_json(connection / "oauth.json", self.token)
        reader = GoogleHealthAPI()
        reader.configure({"timezone": "Asia/Shanghai", "allowed_metrics": ["sleep_minutes"]})
        today = datetime.now(timezone.utc).date() - timedelta(days=1)
        data = point("sleep", 450)
        data["sleep"]["interval"]["endTime"] = today.isoformat() + "T00:00:00Z"
        with patch("google.oauth2.credentials.Credentials.from_authorized_user_info", return_value=self.credentials), patch("google.auth.transport.requests.AuthorizedSession") as session:
            session.return_value.__enter__.return_value.get.return_value = SimpleNamespace(status_code=200, content=b"{}", json=lambda: {"dataPoints": [data]})
            self.assertEqual(len(list(reader.read(connection, "synthetic"))), 1)
            calls = session.return_value.__enter__.return_value.get.call_args_list
            self.assertEqual(len(calls), 1)
            self.assertIn("/dataTypes/sleep/", calls[0].args[0])
        session.get = lambda *a, **kw: SimpleNamespace(status_code=403)
        with self.assertRaises(ValueError):
            fetch_points(session, ["sleep_minutes"], AS_OF, AS_OF, "Asia/Shanghai")


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        path, _ = demo(self.root)
        self.profile = make_profile("demo-user", "synthetic personal concern", ["sleep", "recovery"], "jsonl", str(path),
                                    ["sleep_minutes", "resting_heart_rate_bpm", "hrv_rmssd_ms"], True, True,
                                    answers={"sleep": "synthetic private context"}, now=NOW - timedelta(days=40))
        self.box = Outbox(self.root / "care.sqlite3")

    def tearDown(self):
        self.box.close()
        self.temp.cleanup()

    def output(self):
        return care_once(self.profile, self.root, AS_OF, NOW)

    def tick(self, now=NOW, settings=None, **kwargs):
        return report_tick(self.profile, self.output(), self.root, now, self.box,
                           settings or {"enabled": True, "interval_days": 7}, **kwargs)

    def test_complete_report_contains_missingness_evidence_baseline_and_context(self):
        result = self.tick()
        self.assertEqual(result["status"], "sent")
        report = result["latest"]
        self.assertIn("方法与证据边界", report["markdown"])
        self.assertIn("synthetic private context", report["markdown"])
        self.assertTrue((self.root / "reports" / (report["id"] + ".md")).exists())
        self.assertEqual(len(report["metrics"]), 3)
        self.assertTrue(all(s["valid_days"] == 7 for s in report["metrics"]))

    def test_cadence_and_manual_rerun_do_not_duplicate(self):
        first = self.tick()
        self.assertEqual(self.tick()["status"], "waiting_for_next_period")
        self.assertEqual(self.tick(force=True)["latest"]["id"], first["latest"]["id"])
        self.assertEqual(self.box.db.execute("SELECT COUNT(*) FROM health_reports").fetchone()[0], 1)

    def test_disabled_report_never_calls_model_or_transport(self):
        with patch("healthos.reports.build_report") as build:
            self.tick(settings={"enabled": False})
            build.assert_not_called()

    def test_revocation_blocks_api_reader_and_report(self):
        self.profile["sources"][0]["adapter"] = "google-health-api"
        for grant in self.profile["consents"]:
            grant["revoked_at"] = NOW.isoformat()
        with patch("healthos.permissions.get_adapter") as load:
            observations, _ = collect(self.profile, self.root, NOW)
            self.assertEqual(observations, [])
            load.assert_not_called()
        self.assertEqual(self.tick()["status"], "disabled_or_not_authorized")

    def test_every_report_metric_needs_notification_permission(self):
        self.profile["consents"][1]["metrics"] = ["sleep_minutes"]
        self.assertEqual(self.tick()["status"], "waiting_for_data_or_report_permission")

    def test_cloud_packet_excludes_identifiers_records_and_user_text(self):
        output = self.output()
        packet = agent_packet(self.profile, output, [])
        public = json.dumps(cloud_packet(packet))
        for private in ("demo-user", "synthetic private context", "synthetic personal concern", "demo-device", str(self.root)):
            self.assertNotIn(private, public)
        self.assertIn("missing_days", public)

    def test_model_requires_opt_in_and_failure_preserves_local_report(self):
        with self.assertRaises(ValueError):
            render_ai(agent_packet(self.profile, self.output(), []), {"provider": "openai_compatible"})
        with patch("healthos.reports.render_ai", side_effect=RuntimeError("synthetic secret must not be persisted")):
            report = build_report(self.profile, self.output(), [], NOW, {"llm": {"provider": "openai_compatible", "share_aggregates": True}})
        self.assertEqual(report["ai_status"], "failed_using_source_backed_report")
        self.assertNotIn("secret must", json.dumps(report))
        self.assertTrue(report["next_actions"])

    def test_memory_pauses_unsuitable_action_without_changing_baseline_rule(self):
        output = self.output()
        feedback = [{"action_id": "sleep-routine-v1", "status": "not_relevant"}]
        report = build_report(self.profile, output, feedback, NOW)
        self.assertIn("sleep-routine-v1", report["memory"]["paused_actions"])
        self.assertFalse(any(a["advice"]["action_id"] == "sleep-routine-v1" for a in report["next_actions"]))
        self.assertEqual(report["personal_trends"], output["report"]["results"])

    def test_external_transport_requires_all_consents_and_matching_recipient(self):
        with patch("healthos.reports.get_delivery") as transport:
            result = self.tick(delivery={"plugin": "fake:Transport", "recipient_user_id": "demo-user"}, allow_external=True)
            self.assertEqual(result["status"], "external_delivery_not_authorized")
            transport.assert_not_called()

    def test_uncertain_delivery_is_not_retried(self):
        self.profile["consents"][2]["granted"] = True
        self.profile["consents"][2]["granted_at"] = (NOW - timedelta(days=40)).isoformat()
        class Transport:
            def send_report(self, report, settings):
                raise DeliveryUncertain("synthetic timeout")
        with patch("healthos.reports.get_delivery", return_value=Transport()) as load:
            args = {"delivery": {"plugin": "fake:Transport", "recipient_user_id": "demo-user"}, "allow_external": True}
            self.assertEqual(self.tick(**args)["status"], "uncertain")
            self.assertEqual(self.tick(force=True, **args)["status"], "uncertain")
            self.assertEqual(load.call_count, 1)

    def test_forget_memory_clears_generated_history_keeps_exports(self):
        self.tick()
        forget_memory(self.profile, self.root)
        self.assertTrue((self.root / "synthetic_observations.jsonl").exists())
        self.assertFalse((self.root / "memory.json").exists())
        self.assertEqual(self.profile["clarification_answers"], {})
        self.assertEqual(list((self.root / "reports").iterdir()), [])
        self.assertEqual(self.box.db.execute("SELECT COUNT(*) FROM health_reports").fetchone()[0], 0)

    def test_saved_configuration_runs_through_existing_cycle(self):
        write_json(self.root / "report-settings.json", {"enabled": True, "interval_days": 7})
        output = cycle(self.profile, self.root, NOW)
        self.assertEqual(output["periodic_report"]["status"], "sent")
        self.assertTrue((self.root / "agent-packet.json").exists())


if __name__ == "__main__":
    unittest.main()
