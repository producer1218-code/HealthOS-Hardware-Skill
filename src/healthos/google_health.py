"""Experimental Google Health v4 read-only connector, using Google OAuth libraries.

Live access requires an eligible Cloud project. No credentials are bundled.
Reference: https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints/list
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from healthos.model import METRICS, Observation, parse_timestamp
from healthos.monitor import write_json

BASE = "https://health.googleapis.com/v4/users/me"
TYPES = {
    "resting_heart_rate_bpm": ("daily-resting-heart-rate", "daily_resting_heart_rate.date", "health_metrics_and_measurements"),
    "hrv_rmssd_ms": ("daily-heart-rate-variability", "daily_heart_rate_variability.date", "health_metrics_and_measurements"),
    "sleep_minutes": ("sleep", "sleep.interval.end_time", "sleep"),
}


def scopes_for(metrics):
    if not metrics or set(metrics) - TYPES.keys():
        raise ValueError("Google live connector supports RHR, daily RMSSD and sleep only")
    return sorted({"https://www.googleapis.com/auth/googlehealth." + TYPES[m][2] + ".readonly" for m in metrics})


def authorize(client_file: Path, connection: Path, metrics: list[str], port: int = 8766, encrypted_storage_confirmed: bool = False):
    """User-started browser flow. Token is saved only after account-link verification."""
    if encrypted_storage_confirmed is not True:
        raise ValueError("Google requires encrypted health data and credentials at rest. Put the entire private workspace on encrypted storage and explicitly confirm it.")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import AuthorizedSession
    except ImportError:
        raise ValueError('Install the optional connector: pip install -e ".[google]"') from None
    config = json.loads(client_file.read_text(encoding="utf-8"))
    client = config.get("installed", config.get("web", {}))
    if client.get("auth_uri") != "https://accounts.google.com/o/oauth2/auth" or client.get("token_uri") != "https://oauth2.googleapis.com/token":
        raise ValueError("Use the original OAuth client JSON downloaded from Google Cloud")
    requested = scopes_for(metrics)
    flow = InstalledAppFlow.from_client_config(config, requested, autogenerate_code_verifier=True)
    credentials = flow.run_local_server(host="127.0.0.1", port=port, access_type="offline", prompt="consent", timeout_seconds=180)
    if not credentials.refresh_token:
        raise ValueError("No offline refresh token; re-authorize before scheduling")
    with AuthorizedSession(credentials) as session:
        response = session.get(BASE + "/identity", timeout=20, allow_redirects=False)
        if response.status_code != 200:
            raise ValueError("Google Health account is not linked or API access is unavailable; see the connection guide")
    connection.mkdir(parents=True, exist_ok=True)
    token = json.loads(credentials.to_json())
    token["scopes"] = list(credentials.granted_scopes or credentials.scopes or [])
    if not set(requested) <= set(token["scopes"]):
        raise ValueError("Requested health scopes were not granted")
    write_json(connection / "oauth.json", token)
    (connection / "oauth.json").chmod(0o600)
    write_json(connection / "connection.json", {"version": "google-health-v4-experimental", "metrics": metrics,
                                               "encrypted_storage_confirmed": True,
                                               "authorized_at": datetime.now(timezone.utc).isoformat()})


def fetch_points(session, metrics, start: date, end: date, timezone_name: str):
    """All-or-nothing bounded, paginated fetch; no silent partial snapshot."""
    points = []
    zone = ZoneInfo(timezone_name)
    for metric in sorted(metrics):
        datatype, field, _ = TYPES[metric]
        lo, hi = start.isoformat(), (end + timedelta(days=1)).isoformat()
        if metric == "sleep_minutes":
            # Sleep filtering is by waking/end time, as required by the Google filters guide.
            lo = datetime.combine(start, time.min, zone).astimezone(timezone.utc).isoformat()
            hi = datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(timezone.utc).isoformat()
        params = {"pageSize": 25 if metric == "sleep_minutes" else 1000,
                  "filter": f'{field} >= "{lo}" AND {field} < "{hi}"',
                  "dataSourceFamily": "users/me/dataSourceFamilies/google-wearables"}
        seen = set()
        for _ in range(200):
            response = session.get(BASE + f"/dataTypes/{datatype}/dataPoints", params=params, timeout=20, allow_redirects=False)
            if response.status_code != 200:
                raise ValueError(f"Google Health read failed (HTTP {response.status_code}); check access, scopes and account linking")
            if len(response.content) > 4_000_000:
                raise ValueError("Google Health page exceeds local limit")
            page = response.json()
            if not isinstance(page.get("dataPoints", []), list):
                raise ValueError("Invalid Google Health page")
            points.extend(page.get("dataPoints", []))
            next_token = page.get("nextPageToken")
            if not next_token:
                break
            if next_token in seen:
                raise ValueError("Repeated Google Health pagination token")
            seen.add(next_token)
            params["pageToken"] = next_token
        else:
            raise ValueError("Google Health pagination limit exceeded")
    return {"dataPoints": points, "window": [start.isoformat(), end.isoformat()], "timezone": timezone_name}


class GoogleHealthSnapshot:
    """Strict Fitbit-only subset. Unknown provenance/processing is skipped, not guessed."""
    def configure(self, settings):
        self.settings = settings

    def read(self, path: Path, user_id: str):
        yield from self.parse(json.loads(path.read_text(encoding="utf-8")), user_id)

    def parse(self, payload: dict, user_id: str):
        settings = getattr(self, "settings", {})
        zone = ZoneInfo(settings.get("timezone", "Asia/Shanghai"))
        allowed = set(settings.get("allowed_metrics", TYPES))
        self.diagnostics = {"skipped_records": 0, "invalid_records": 0, "device_identity": "provisional_metadata_not_hardware_id"}
        if not isinstance(payload.get("dataPoints"), list):
            raise ValueError("Snapshot requires dataPoints list")
        seen, records = {}, {}
        for point in payload["dataPoints"]:
            try:
                provenance = point.get("dataSource", {})
                if provenance.get("platform") != "FITBIT" or not provenance.get("device", {}).get("displayName"):
                    self.diagnostics["skipped_records"] += 1
                    continue
                device = "google-metadata:" + sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()[:20]
                method = "daily"
                if "dailyRestingHeartRate" in point:
                    metric, record = "resting_heart_rate_bpm", point["dailyRestingHeartRate"]
                    method = record.get("dailyRestingHeartRateMetadata", {}).get("calculationMethod")
                    if method not in {"WITH_SLEEP", "ONLY_WITH_AWAKE_DATA"}:
                        raise ValueError("RHR calculation method missing")
                    value = float(record["beatsPerMinute"])
                elif "dailyHeartRateVariability" in point:
                    metric, record = "hrv_rmssd_ms", point["dailyHeartRateVariability"]
                    # Deep sleep RMSSD is a different statistic and is never substituted.
                    value = float(record["averageHeartRateVariabilityMilliseconds"])
                elif "sleep" in point:
                    metric, record = "sleep_minutes", point["sleep"]
                    metadata = record.get("metadata", {})
                    main_sleep = metadata.get("mainSleep", metadata.get("main"))
                    if metadata.get("processed") is not True or main_sleep is not True or metadata.get("manuallyEdited") is True or (
                            "mainSleep" in metadata and "main" in metadata and metadata["mainSleep"] != metadata["main"]):
                        self.diagnostics["skipped_records"] += 1
                        continue
                    stamp = parse_timestamp(record["interval"]["endTime"]).astimezone(zone)
                    value = float(record["summary"]["minutesAsleep"])
                else:
                    self.diagnostics["skipped_records"] += 1
                    continue
                if metric not in allowed:
                    continue
                if metric != "sleep_minutes":
                    d = record["date"]
                    stamp = datetime(d["year"], d["month"], d["day"], 12, tzinfo=zone)
                if value < 0 or (metric == "sleep_minutes" and value > 1440):
                    raise ValueError("Invalid metric")
                if payload.get("window") and not payload["window"][0] <= stamp.date().isoformat() <= payload["window"][1]:
                    continue
                source = "google-health/FITBIT/" + metric + "/" + method
                item = Observation(user_id, stamp.isoformat(), metric, value, METRICS[metric][0], source, device,
                                   context="daily civil-date anchor or main-sleep waking time; provisional metadata identity; parsing quality only")
                key = (source, device, stamp.date())
                if key in seen and seen[key] != value:
                    records[key] = None  # Conflicting daily records invalidate this day.
                    self.diagnostics["invalid_records"] += 1
                elif key not in seen:
                    records[key] = item
                seen[key] = value
            except (KeyError, ValueError, TypeError, OverflowError):
                self.diagnostics["invalid_records"] += 1
        yield from (o for o in records.values() if o is not None)


class GoogleHealthAPI(GoogleHealthSnapshot):
    def read(self, path: Path, user_id: str):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import AuthorizedSession
        except ImportError:
            raise ValueError('Install pip install -e ".[google]" first') from None
        config = json.loads((path / "connection.json").read_text(encoding="utf-8"))
        if config.get("encrypted_storage_confirmed") is not True:
            raise ValueError("Encrypted storage confirmation is required for API health records and credentials")
        allowed = set(self.settings["allowed_metrics"]) & set(config["metrics"]) & TYPES.keys()
        if not allowed:
            return
        token_file = path / "oauth.json"
        token = json.loads(token_file.read_text(encoding="utf-8"))
        if token.get("token_uri") != "https://oauth2.googleapis.com/token" or not set(scopes_for(allowed)) <= set(token.get("scopes", [])):
            raise ValueError("Google credential endpoint or granted scopes do not match")
        credentials = Credentials.from_authorized_user_info(token)
        end = datetime.now(ZoneInfo(self.settings["timezone"])).date() - timedelta(days=1)
        with AuthorizedSession(credentials) as session:
            payload = fetch_points(session, allowed, end - timedelta(days=44), end, self.settings["timezone"])
        write_json(token_file, json.loads(credentials.to_json()))
        token_file.chmod(0o600)
        write_json(path / "snapshot.json", payload)
        yield from self.parse(payload, user_id)
