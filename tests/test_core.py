from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

from healthos.adapters import get_adapter
from healthos.analysis import analyze
from healthos.cli import demo
from healthos.model import METRICS, Observation


def obs(day: date, metric: str, value: float, device: str = "a", quality: float = 1.0):
    stamp = datetime(day.year, day.month, day.day, 9, tzinfo=timezone.utc).isoformat()
    return Observation("u", stamp, metric, value, METRICS[metric][0], "test", device, quality)


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (Path(__file__).parent / "_work").mkdir(parents=True, exist_ok=True)

    def test_timestamp_and_unit_validation(self):
        with self.assertRaises(ValueError):
            Observation("u", "2026-07-01T10:00:00", "heart_rate_bpm", 60, "bpm", "x", "d")
        with self.assertRaises(ValueError):
            Observation("u", "2026-07-01T10:00:00+00:00", "heart_rate_bpm", 60, "ms", "x", "d")

    def test_no_unmeasured_data_imputed(self):
        start = date(2026, 7, 1)
        data = [obs(start + timedelta(days=i), "resting_heart_rate_bpm", 60) for i in range(16)]
        result = analyze(data, date(2026, 7, 19))["results"][0]
        self.assertEqual(result["status"], "insufficient_recent_data")
        self.assertEqual(result["recent_n_days"], 0)

    def test_device_change_cannot_inherit_baseline(self):
        start = date(2026, 7, 1)
        data = [obs(start + timedelta(days=i), "resting_heart_rate_bpm", 58, "old") for i in range(28)]
        data += [obs(start + timedelta(days=i), "resting_heart_rate_bpm", 75, "new") for i in range(28, 31)]
        results = analyze(data, date(2026, 7, 31))["results"]
        self.assertEqual({item["status"] for item in results}, {"calibrating", "insufficient_recent_data"})

    def test_persistent_change_and_quality_gate(self):
        start = date(2026, 7, 1)
        data = [obs(start + timedelta(days=i), "resting_heart_rate_bpm", 58 + i % 2) for i in range(28)]
        data += [obs(start + timedelta(days=i), "resting_heart_rate_bpm", 69) for i in range(28, 31)]
        data.append(obs(date(2026, 7, 1), "resting_heart_rate_bpm", 150, quality=0.1))
        report = analyze(data, date(2026, 7, 31))
        self.assertEqual(report["rejected"]["low_quality"], 1)
        self.assertEqual(report["results"][0]["status"], "notable_change")
        self.assertAlmostEqual(report["results"][0]["baseline_median"], 58.5)

    def test_apple_export_and_whoop_fixture(self):
        root = Path(__file__).parent / "_work"
        xml = root / "test_export.xml"
        xml.write_text('''<HealthData><Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Watch" unit="count/min" endDate="2026-07-01 08:00:00 +0800" value="65"/><Record type="HKQuantityTypeIdentifierOxygenSaturation" sourceName="Watch" unit="%" endDate="2026-07-01 08:00:00 +0800" value="0.97"/><Record type="HKQuantityTypeIdentifierStepCount" sourceName="Watch" unit="count" endDate="2026-07-01 08:00:00 +0800" value="50"/></HealthData>''', encoding="utf-8")
        apple = list(get_adapter("apple-health-xml").read(xml, "u"))
        self.assertEqual(len(apple), 2)
        self.assertEqual(apple[1].value, 97)
        whoop = root / "test_whoop.json"
        whoop.write_text(json.dumps({"kind":"recovery", "records":[{"created_at":"2026-07-01T08:00:00Z", "score_state":"SCORED", "score":{"resting_heart_rate":60,"hrv_rmssd_milli":40}}]}), encoding="utf-8")
        metrics = {item.metric for item in get_adapter("whoop-v2-json").read(whoop, "u")}
        self.assertEqual(metrics, {"resting_heart_rate_bpm", "hrv_rmssd_ms"})

    def test_demo_is_reproducible(self):
        data_file, report_file = demo(Path(__file__).parent / "_work")
        self.assertEqual(len(data_file.read_text(encoding="utf-8").splitlines()), 155)
        results = json.loads(report_file.read_text(encoding="utf-8"))["results"]
        self.assertIn("notable_change", {item["status"] for item in results})


if __name__ == "__main__":
    unittest.main()
