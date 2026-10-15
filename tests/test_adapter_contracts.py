"""Synthetic contract regressions for the bundled Apple, WHOOP and Google readers."""
import json
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest

from healthos.adapters.apple_export import AppleHealthExport
from healthos.adapters.google_health_rhr import GoogleHealthRestingHeartRate
from healthos.adapters.whoop_json import WhoopV2JSON
from healthos.model import METRICS, parse_timestamp


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def apple_record(kind="HKQuantityTypeIdentifierRestingHeartRate", unit="count/min",
                 value="60", source="Synthetic Watch", end="2026-07-01 08:00:00 +0800"):
    return f'<Record type="{kind}" sourceName="{source}" unit="{unit}" endDate="{end}" value="{value}"/>'


def whoop_recovery(**fields):
    score = {"resting_heart_rate": 60, "hrv_rmssd_milli": 40,
             "spo2_percentage": 97, "skin_temp_celsius": 33.7}
    score.update(fields.pop("score", {}) or {})
    return {"created_at": "2026-07-01T08:00:00Z", "score_state": "SCORED", "score": score, **fields}


def google_point(bpm=58, platform="FITBIT", device="Synthetic Band",
                 method="OMITTED_MEASUREMENTS_AVERAGE", day=(2026, 7, 1)):
    data_source = {} if platform is None else {"platform": platform, "device": {"displayName": device}}
    stamp = None if day is None else {"year": day[0], "month": day[1], "day": day[2]}
    return {"dataSource": data_source,
            "dailyRestingHeartRate": {"beatsPerMinute": bpm,
                                      "dailyRestingHeartRateMetadata": {"calculationMethod": method},
                                      "date": stamp}}


class AppleExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, filename, text):
        path = self.root / filename
        path.write_text(text, encoding="utf-8")
        return path

    def test_bundled_example_yields_expected_observations(self):
        rows = list(AppleHealthExport().read(EXAMPLES / "apple_export_example.xml", "u"))
        self.assertEqual([(o.metric, o.value, o.unit) for o in rows],
                         [("resting_heart_rate_bpm", 60.0, "bpm"),
                          ("hrv_sdnn_ms", 43.0, "ms"),
                          ("spo2_pct", 97.0, "%")])
        for o in rows:
            self.assertEqual(o.unit, METRICS[o.metric][0])
            self.assertEqual(o.source, "apple-health-export")
            self.assertEqual(o.device_id, "Synthetic Watch")
            self.assertEqual(o.timestamp, "2026-07-01T08:00:00+08:00")
            self.assertEqual(parse_timestamp(o.timestamp).utcoffset(), timedelta(hours=8))

    def test_unknown_type_unit_mismatch_and_step_records_are_ignored(self):
        text = "<HealthData>" + apple_record(kind="HKQuantityTypeIdentifierHeartRate", unit="bpm", value="72") \
               + apple_record(kind="HKQuantityTypeIdentifierStepCount", unit="count", value="3000") \
               + apple_record(kind="HKQuantityTypeIdentifierMindfulSession", unit="min", value="5") + "</HealthData>"
        path = self.save("ignored.xml", text)
        self.assertEqual(list(AppleHealthExport().read(path, "u")), [])

    def test_spo2_fraction_is_scaled_but_out_of_range_value_is_rejected(self):
        path = self.save("spo2_fraction.xml", "<HealthData>"
            + apple_record(kind="HKQuantityTypeIdentifierOxygenSaturation", unit="%", value="0.5") + "</HealthData>")
        self.assertEqual([o.value for o in AppleHealthExport().read(path, "u")], [50.0])
        bad = self.save("spo2_bad.xml", "<HealthData>"
            + apple_record(kind="HKQuantityTypeIdentifierOxygenSaturation", unit="%", value="-1") + "</HealthData>")
        with self.assertRaises(ValueError):
            list(AppleHealthExport().read(bad, "u"))

    def test_non_numeric_value_is_rejected_instead_of_guessed(self):
        path = self.save("bad_value.xml", "<HealthData>"
            + apple_record(kind="HKQuantityTypeIdentifierHeartRate", unit="count/min", value="not-a-number") + "</HealthData>")
        with self.assertRaises(ValueError):
            list(AppleHealthExport().read(path, "u"))

    def test_record_without_source_name_falls_back_to_unknown_device(self):
        raw = '<Record type="HKQuantityTypeIdentifierRestingHeartRate" unit="count/min" endDate="2026-07-01 08:00:00 +0800" value="60"/>'
        path = self.save("no_source.xml", "<HealthData>" + raw + "</HealthData>")
        self.assertEqual([o.device_id for o in AppleHealthExport().read(path, "u")], ["unknown"])

    def test_dates_without_records_produce_nothing(self):
        path = self.save("one_day.xml", "<HealthData>" + apple_record() + "</HealthData>")
        rows = list(AppleHealthExport().read(path, "u"))
        # 2026-07-02 has no Record, so it must not show up at all.
        self.assertEqual({o.timestamp[:10] for o in rows}, {"2026-07-01"})


class WhoopJsonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, filename, payload):
        path = self.root / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_bundled_example_yields_expected_recovery_fields(self):
        rows = list(WhoopV2JSON().read(EXAMPLES / "whoop_recovery_example.json", "u"))
        self.assertEqual([(o.metric, o.value, o.unit) for o in rows],
                         [("resting_heart_rate_bpm", 60.0, "bpm"),
                          ("hrv_rmssd_ms", 40.0, "ms"),
                          ("spo2_pct", 97.0, "%"),
                          ("skin_temp_c", 33.7, "degC")])
        for o in rows:
            self.assertEqual(o.unit, METRICS[o.metric][0])
            self.assertEqual((o.source, o.device_id, o.context),
                             ("whoop-v2-api", "whoop-v2", "recovery_score"))
            self.assertEqual(parse_timestamp(o.timestamp).utcoffset(), timedelta(0))

    def test_sleep_payload_sums_stages_and_keeps_respiratory_rate(self):
        score = {"stage_summary": {"total_light_sleep_time_milli": 120000,
                                   "total_slow_wave_sleep_time_milli": 60000,
                                   "total_rem_sleep_time_milli": 40000},
                 "respiratory_rate": 15.5}
        record = {"created_at": "2026-07-01T08:00:00Z", "end": "2026-07-01T09:30:00Z",
                  "score_state": "SCORED", "score": score}
        path = self.save("sleep.json", {"kind": "sleep", "records": [record]})
        rows = list(WhoopV2JSON().read(path, "u"))
        self.assertEqual([o.metric for o in rows], ["sleep_minutes", "respiratory_rate_bpm"])
        self.assertAlmostEqual(rows[0].value, 11 / 3)
        self.assertEqual(rows[0].unit, METRICS["sleep_minutes"][0])
        self.assertEqual(rows[0].context, "sum_of_sleep_stages")
        self.assertEqual(rows[1].value, 15.5)
        self.assertEqual(rows[1].unit, "breaths/min")

    def test_nap_sleep_records_are_skipped_entirely(self):
        score = {"stage_summary": {"total_light_sleep_time_milli": 1000,
                                   "total_slow_wave_sleep_time_milli": 1000,
                                   "total_rem_sleep_time_milli": 1000},
                 "respiratory_rate": 16}
        record = {"created_at": "2026-07-01T08:00:00Z", "score_state": "SCORED",
                  "nap": True, "score": score}
        path = self.save("nap.json", {"kind": "sleep", "records": [record]})
        self.assertEqual(list(WhoopV2JSON().read(path, "u")), [])

    def test_pending_or_scoreless_recovery_records_are_skipped(self):
        scoreless = {"created_at": "2026-07-01T08:00:00Z", "score_state": "SCORED", "score": None}
        records = [whoop_recovery(score_state="PENDING_SCORE"), scoreless, whoop_recovery()]
        path = self.save("mixed_state.json", {"kind": "recovery", "records": records})
        rows = list(WhoopV2JSON().read(path, "u"))
        # Only the fully scored record may contribute, so four observations, not eight.
        self.assertEqual(len(rows), 4)
        self.assertEqual({o.metric for o in rows},
                         {"resting_heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "skin_temp_c"})

    def test_unknown_kind_or_broken_payload_is_rejected(self):
        path = self.save("broken.json", {"kind": "steps", "records": []})
        with self.assertRaises(ValueError):
            list(WhoopV2JSON().read(path, "u"))
        path.write_text(json.dumps({"kind": "recovery", "records": {"cycle_id": 1}}), encoding="utf-8")
        with self.assertRaises(ValueError):
            list(WhoopV2JSON().read(path, "u"))
        path.write_text(json.dumps([whoop_recovery()]), encoding="utf-8")
        with self.assertRaises(ValueError):
            list(WhoopV2JSON().read(path, "u"))

    def test_records_without_timestamp_or_complete_stages_are_skipped(self):
        no_stamp = whoop_recovery(created_at=None)
        path = self.save("no_stamp.json", {"kind": "recovery", "records": [no_stamp]})
        self.assertEqual(list(WhoopV2JSON().read(path, "u")), [])
        partial = {"created_at": "2026-07-01T08:00:00Z", "score_state": "SCORED",
                   "score": {"stage_summary": {"total_light_sleep_time_milli": 120000}}}
        path.write_text(json.dumps({"kind": "sleep", "records": [partial]}), encoding="utf-8")
        self.assertEqual(list(WhoopV2JSON().read(path, "u")), [])

    def test_dates_without_records_produce_nothing(self):
        path = self.save("one_day.json", {"kind": "recovery", "records": [whoop_recovery()]})
        rows = list(WhoopV2JSON().read(path, "u"))
        # 2026-07-02 has no cycle record, so it must not show up at all.
        self.assertEqual({o.timestamp[:10] for o in rows}, {"2026-07-01"})


class GoogleRestingHeartRateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, filename, payload):
        path = self.root / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_saved_point_anchors_to_local_noon_with_provenance(self):
        path = self.save("snapshot.json", {"points": [google_point()]})
        rows = list(GoogleHealthRestingHeartRate().read(path, "u"))
        self.assertEqual([(o.metric, o.value, o.unit) for o in rows],
                         [("resting_heart_rate_bpm", 58.0, "bpm")])
        row = rows[0]
        self.assertEqual(row.timestamp, "2026-07-01T12:00:00+08:00")
        self.assertEqual(row.source, "google-health/FITBIT/OMITTED_MEASUREMENTS_AVERAGE")
        self.assertEqual(row.device_id, "display-name:Synthetic Band")
        self.assertEqual(parse_timestamp(row.timestamp).utcoffset(), timedelta(hours=8))

    def test_non_fitbit_or_incomplete_points_are_skipped(self):
        payload = {"points": [google_point(platform="RECORDED"), google_point(device=None),
                              google_point(method=None), google_point(day=None)]}
        path = self.save("incomplete.json", payload)
        self.assertEqual(list(GoogleHealthRestingHeartRate().read(path, "u")), [])

    def test_snapshot_without_points_list_is_rejected(self):
        path = self.save("broken.json", {"points": {"cycle_id": 1}})
        with self.assertRaises(ValueError):
            list(GoogleHealthRestingHeartRate().read(path, "u"))
        path.write_text(json.dumps({"dataPoints": []}), encoding="utf-8")
        with self.assertRaises(ValueError):
            list(GoogleHealthRestingHeartRate().read(path, "u"))

    def test_impossible_civil_date_is_rejected(self):
        path = self.save("bad_date.json", {"points": [google_point(day=(2026, 2, 30))]})
        with self.assertRaises(ValueError):
            list(GoogleHealthRestingHeartRate().read(path, "u"))

    def test_same_day_points_are_both_kept_for_the_report_median(self):
        payload = {"points": [google_point(bpm=58), google_point(bpm=61)]}
        path = self.save("duplicate_day.json", payload)
        rows = list(GoogleHealthRestingHeartRate().read(path, "u"))
        self.assertEqual([o.value for o in rows], [58.0, 61.0])
        self.assertEqual({o.timestamp for o in rows}, {"2026-07-01T12:00:00+08:00"})

    def test_dates_without_points_produce_nothing(self):
        path = self.save("one_day.json", {"points": [google_point()]})
        rows = list(GoogleHealthRestingHeartRate().read(path, "u"))
        # only 2026-07-01 has a saved point, so nothing may appear for 2026-07-02.
        self.assertEqual({o.timestamp[:10] for o in rows}, {"2026-07-01"})


if __name__ == "__main__":
    unittest.main()
