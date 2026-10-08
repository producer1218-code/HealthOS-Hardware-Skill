"""User-downloaded Fitbit/Google Health directory, ZIP, or supported file.

Only named, observed export subsets are parsed. ZIPs are never extracted.
https://support.google.com/googlehealth/answer/14236615
https://dev.fitbit.com/build/reference/web-api/sleep/
"""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime, time
import io
import json
from math import isfinite
from pathlib import Path, PurePosixPath
import zipfile
from zoneinfo import ZoneInfo

from healthos.model import METRICS, Observation


MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 10000


def file_kind(name: str) -> str | None:
    name = PurePosixPath(name.replace("\\", "/")).name.lower()
    if name == "daily_resting_heart_rate.csv":
        return "rhr"
    if name == "daily_heart_rate_variability.csv" or (name.startswith("daily heart rate variability summary") and name.endswith(".csv")):
        return "hrv"
    if name.startswith("usersleeps_") and name.endswith(".csv"):
        return "sleep_csv"
    if name.startswith("sleep-") and name.endswith(".json"):
        return "sleep_json"
    if name.startswith("steps_") and name.endswith(".csv"):
        return "steps_csv"
    if name.startswith("steps-") and name.endswith(".json"):
        return "steps_json"
    return None


def export_files(path: Path, allowed_kinds: set[str] | None = None):
    """Yield only supported filenames; bounded archive reads prevent ZIP bombs."""
    total = 0
    def supported(name):
        kind = file_kind(name)
        return bool(kind and (allowed_kinds is None or kind in allowed_kinds))
    if path.is_dir():
        files = sorted(p for p in path.rglob("*") if p.is_file() and not p.is_symlink() and supported(p.name))
        if len(files) > MAX_MEMBERS:
            raise ValueError("导出文件过多，请选择 Fitbit/Google Health 子目录。")
        for file in files:
            size = file.stat().st_size
            total += size
            if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError("导出数据超出本地读取上限，请分批导入。")
            yield file.name, file.read_text(encoding="utf-8-sig")
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > MAX_MEMBERS:
                raise ValueError("ZIP 文件项目过多，请缩小导出范围。")
            for item in sorted(archive.infolist(), key=lambda x: x.filename):
                parts = PurePosixPath(item.filename.replace("\\", "/"))
                if parts.is_absolute() or ".." in parts.parts:
                    raise ValueError("ZIP 包含不安全路径，未读取。")
                if item.is_dir() or "__MACOSX" in parts.parts or not supported(item.filename):
                    continue
                total += item.file_size
                if item.file_size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                    raise ValueError("ZIP 数据超出读取上限，请分批导入。")
                if item.file_size > 1024 * 1024 and item.file_size / max(item.compress_size, 1) > 200:
                    raise ValueError("ZIP 压缩比例异常，未读取。")
                with archive.open(item) as stream:
                    raw = stream.read(MAX_FILE_BYTES + 1)
                if len(raw) > MAX_FILE_BYTES:
                    raise ValueError("文件超出读取上限。")
                yield parts.name, raw.decode("utf-8-sig")
    elif path.is_file() and supported(path.name):
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("文件超出读取上限。")
        yield path.name, path.read_text(encoding="utf-8-sig")
    else:
        raise ValueError("请选择 Fitbit/Google Health 导出目录、ZIP 或受支持的导出文件。")


class FitbitTakeout:
    def __init__(self):
        self.timezone = ZoneInfo("Asia/Shanghai")
        self.device = "declared-fitbit-1"
        self.allowed = set(METRICS)
        self.diagnostics = {}

    def configure(self, settings: dict):
        self.timezone = ZoneInfo(settings.get("timezone", "Asia/Shanghai"))
        self.device = str(settings.get("device_id", "declared-fitbit-1"))
        self.allowed = set(settings.get("allowed_metrics", METRICS))

    def stamp(self, value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            # Legacy Fitbit interval JSON exports use US month/day/year.
            parsed = None
            for pattern in ("%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
                try:
                    parsed = datetime.strptime(value, pattern)
                    break
                except ValueError:
                    continue
            if parsed is None:
                raise ValueError("unsupported export timestamp")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=self.timezone)
            self.diagnostics["assumed_local_timezone"] += 1
        return parsed.astimezone(self.timezone)

    def number(self, value) -> float:
        value = float(value)
        if not isfinite(value) or value < 0:
            raise ValueError("invalid numeric record")
        return value

    def read(self, path: Path, user_id: str):
        self.diagnostics = {"recognized_files": 0, "invalid_rows": 0, "skipped_ambiguous_hrv": 0,
                            "skipped_non_fitbit_source": 0,
                            "assumed_local_timezone": 0, "duplicates": 0,
                            "device_identity": "user_declared_single_device_binding",
                            "quality_definition": "parse integrity; measurement accuracy not validated"}
        values, sleep_sessions, steps = {}, {}, defaultdict(dict)
        conflicted_sleep = set()
        kind_metrics = {"rhr": "resting_heart_rate_bpm", "hrv": "hrv_rmssd_ms", "sleep_csv": "sleep_minutes",
                        "sleep_json": "sleep_minutes", "steps_csv": "steps_count", "steps_json": "steps_count"}
        allowed_kinds = {kind for kind, metric in kind_metrics.items() if metric in self.allowed}
        for filename, text in export_files(path, allowed_kinds):
            kind = file_kind(filename)
            requested = {"rhr": "resting_heart_rate_bpm", "hrv": "hrv_rmssd_ms", "sleep_csv": "sleep_minutes",
                         "sleep_json": "sleep_minutes", "steps_csv": "steps_count", "steps_json": "steps_count"}[kind]
            if requested not in self.allowed:
                continue
            self.diagnostics["recognized_files"] += 1
            rows = json.loads(text) if filename.lower().endswith(".json") else list(csv.DictReader(io.StringIO(text)))
            if not isinstance(rows, list):
                raise ValueError("不支持的 Fitbit JSON 结构，请选择导出的原始文件。")
            for row in rows:
                try:
                    if kind in {"rhr", "hrv"}:
                        origin = row.get("data source") or "fitbit-legacy-export"
                        metric = requested
                        if "apple" in origin.lower():
                            # The generic field cannot establish RMSSD for HealthKit SDNN.
                            self.diagnostics["skipped_non_fitbit_source"] += 1
                            if kind == "hrv":
                                self.diagnostics["skipped_ambiguous_hrv"] += 1
                            continue
                        value = self.number(row["beats per minute"] if kind == "rhr" else
                                            row.get("average heart rate variability milliseconds", row.get("rmssd")))
                        if value == 0:
                            self.diagnostics["invalid_rows"] += 1
                            continue
                        stamp = self.stamp(row["timestamp"])
                        method = "daily-average-rmssd" if kind == "hrv" else "daily-rhr-method-unspecified"
                        source = f"fitbit-takeout/{kind}/{origin}/{method}"
                        identity = (source, metric, stamp.isoformat())
                        if identity in values:
                            self.diagnostics["duplicates"] += 1
                            if values[identity] is None or values[identity].value != value:
                                values[identity] = None
                                self.diagnostics["invalid_rows"] += 1
                                continue
                        values[identity] = Observation(user_id, stamp.isoformat(), metric, value, METRICS[metric][0], source,
                                                       self.device, context="daily export; method/window retained in source; user-declared device binding")
                    elif kind.startswith("sleep"):
                        if kind == "sleep_json" and row.get("mainSleep", row.get("isMainSleep", True)) is False:
                            continue
                        end = self.stamp(row["endTime"] if kind == "sleep_json" else row["sleep_end"])
                        start = self.stamp(row["startTime"] if kind == "sleep_json" else row["sleep_start"])
                        value = self.number(row["minutesAsleep"] if kind == "sleep_json" else row["minutes_asleep"])
                        if end <= start or value > (end - start).total_seconds() / 60 + 1:
                            raise ValueError("invalid sleep interval")
                        origin = row.get("data_source") or "fitbit-legacy-export"
                        algorithm = row.get("algorithm_version", "legacy")
                        source = f"fitbit-takeout/{kind}/{origin}/{algorithm}"
                        sleep_id = str(row.get("sleep_id", row.get("logId", start.isoformat())))
                        updated = self.stamp(row.get("sleep_last_updated", end.isoformat()))
                        key = (source, sleep_id)
                        if key in conflicted_sleep:
                            continue
                        previous = sleep_sessions.get(key)
                        if previous:
                            self.diagnostics["duplicates"] += 1
                            if updated == previous[0] and (start, end, value) != previous[1:]:
                                sleep_sessions.pop(key)
                                conflicted_sleep.add(key)
                                self.diagnostics["invalid_rows"] += 1
                                continue
                        if not previous or updated >= previous[0]:
                            sleep_sessions[key] = (updated, start, end, value)
                    else:
                        stamp = self.stamp(row["dateTime"] if kind == "steps_json" else row["timestamp"])
                        value = self.number(row["value"] if kind == "steps_json" else row["steps"])
                        if not value.is_integer():
                            raise ValueError("fractional step count")
                        origin = row.get("data source") or "fitbit-legacy-export"
                        if "apple" in origin.lower():
                            self.diagnostics["skipped_non_fitbit_source"] += 1
                            continue
                        source = f"fitbit-takeout/{kind}/{origin}/interval-sum"
                        key = (source, stamp.date())
                        previous = steps[key].get(stamp.isoformat())
                        if stamp.isoformat() in steps[key]:
                            self.diagnostics["duplicates"] += 1
                            if previous is None or previous != value:
                                # No revision metadata: do not guess which conflicting row wins.
                                steps[key][stamp.isoformat()] = None
                                self.diagnostics["invalid_rows"] += 1
                                continue
                        steps[key][stamp.isoformat()] = value
                except (KeyError, TypeError, ValueError, OverflowError):
                    self.diagnostics["invalid_rows"] += 1
        if self.diagnostics["recognized_files"] == 0:
            raise ValueError("未找到已授权且受支持的 Fitbit 导出字段。请选择 Google Health/Fitbit 导出，或调整目标与授权。")
        # One longest observed sleep session per wake date. This is explicit,
        # not the total of all sessions, and JSON/CSV instruments stay separate.
        nights = {}
        for (source, _), (_, start, end, minutes) in sleep_sessions.items():
            key = (source, end.date())
            if key not in nights or minutes > nights[key][2]:
                nights[key] = (start, end, minutes)
        for (source, day), (start, end, minutes) in nights.items():
            context = json.dumps({"aggregation": "longest_observed_session_per_wake_date", "sleep_start": start.isoformat(),
                                  "sleep_end": end.isoformat(), "device_identity": "user_declared"})
            yield Observation(user_id, end.isoformat(), "sleep_minutes", minutes, "min", source + "/longest-session", self.device, context=context)
        for (source, day), samples in steps.items():
            if any(v is None for v in samples.values()):
                continue
            yield Observation(user_id, datetime.combine(day, time(12), self.timezone).isoformat(), "steps_count",
                              sum(samples.values()), "count", source, self.device,
                              context=f"sum of exported intervals; {len(samples)} unique timestamps; coverage not inferred")
        yield from (value for value in values.values() if value is not None)
