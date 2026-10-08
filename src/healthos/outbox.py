"""SQLite outbox: consent checked at dispatch; budget counts successful sends."""
from __future__ import annotations

from datetime import datetime, timedelta
from importlib import import_module
import json
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from healthos.model import parse_timestamp
from healthos.permissions import notification_allowed, validate_profile


class DeliveryUncertain(RuntimeError):
    """Provider may have accepted a request; reconcile before retrying."""


class LocalJsonDelivery:
    external = False

    def send(self, notice: dict, settings: dict) -> str:
        root = Path(settings["output_dir"])
        root.mkdir(parents=True, exist_ok=True)
        target = root / (notice["id"] + ".json")
        # Stable ID gives local replay idempotency after a process interruption.
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(notice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(target)
        return target.name


def get_delivery(name: str):
    if name == "local-json":
        return LocalJsonDelivery()
    if ":" not in name:
        raise ValueError("delivery plugin requires module:Class")
    module, cls = name.split(":", 1)
    plugin = getattr(import_module(module), cls)()
    if not callable(getattr(plugin, "send", None)) or not isinstance(getattr(plugin, "external", None), bool):
        raise TypeError("delivery plugin requires external: bool and send(notice, settings)")
    return plugin


class Outbox:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS notices (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, stream_key TEXT NOT NULL,
            payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0, sent_at TEXT, receipt TEXT, error_type TEXT
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY, notice_id TEXT NOT NULL, user_id TEXT NOT NULL,
            action_id TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
            note TEXT NOT NULL, created_at TEXT NOT NULL
        );
        """)

    def close(self):
        self.db.close()

    def enqueue(self, output: dict) -> int:
        count = 0
        with self.db:
            for notice in output["candidates"]:
                if notice["user_id"] != output["user_id"]:
                    raise ValueError("candidate user mismatch")
                cursor = self.db.execute("INSERT OR IGNORE INTO notices(id,user_id,stream_key,payload) VALUES(?,?,?,?)",
                                         (notice["id"], notice["user_id"], notice["stream_key"], json.dumps(notice, ensure_ascii=False)))
                count += cursor.rowcount
        return count

    def record_feedback(self, user_id: str, notice_id: str, status: str, now: datetime, note: str = "") -> None:
        execution = {"executed", "skipped", "not_relevant"}
        outcomes = {"felt_better", "unchanged", "felt_worse"}
        if status not in execution | outcomes:
            raise ValueError("feedback must be an execution status or a separate self-reported outcome")
        row = self.db.execute("SELECT payload,status FROM notices WHERE id=? AND user_id=?", (notice_id, user_id)).fetchone()
        if row is None or row["status"] != "sent":
            raise ValueError("feedback requires a delivered notice owned by this user")
        notice = json.loads(row["payload"])
        with self.db:
            self.db.execute("INSERT INTO feedback(notice_id,user_id,action_id,kind,status,note,created_at) VALUES(?,?,?,?,?,?,?)",
                            (notice_id, user_id, notice["advice"]["action_id"],
                             "execution" if status in execution else "self_reported_outcome", status, note[:1000], now.isoformat()))

    def feedback_for(self, user_id: str) -> list[dict]:
        return [dict(row) for row in self.db.execute("SELECT * FROM feedback WHERE user_id=? ORDER BY id", (user_id,))]

    def dispatch(self, profile: dict, now: datetime, settings: dict, allow_external: bool = False) -> dict:
        validate_profile(profile)
        if now.tzinfo is None:
            raise ValueError("dispatch time must have a timezone")
        summary = {"sent": 0, "failed": 0, "uncertain": 0, "cancelled": 0, "expired": 0, "deferred": 0}
        preferences = profile.get("preferences", {})
        budget = preferences.get("max_notices_per_7_days", 2)
        plugin = None
        # Serialize one dispatch worker, including transport acknowledgement.
        # Remote plugins must use notice.id as the provider's idempotency key.
        self.db.execute("BEGIN IMMEDIATE")
        try:
            sent = list(self.db.execute("SELECT stream_key,sent_at FROM notices WHERE user_id=? AND status IN ('sent','uncertain')", (profile["user_id"],)))
            rows = list(self.db.execute("SELECT * FROM notices WHERE user_id=? AND status IN ('pending','failed') ORDER BY rowid", (profile["user_id"],)))
            for row in rows:
                notice = json.loads(row["payload"])
                if not notification_allowed(profile, notice["source_id"], notice["metric"], now):
                    self.db.execute("UPDATE notices SET status='cancelled',payload='{}' WHERE id=?", (row["id"],))
                    summary["cancelled"] += 1
                    continue
                if parse_timestamp(notice["expires_at"]) <= now:
                    self.db.execute("UPDATE notices SET status='expired',payload='{}' WHERE id=?", (row["id"],))
                    summary["expired"] += 1
                    continue
                if notice["advice"]["action_id"] in preferences.get("disabled_actions", []) or any(
                    f["action_id"] == notice["advice"]["action_id"] and f["status"] in {"not_relevant", "felt_worse"}
                    for f in self.feedback_for(profile["user_id"])):
                    self.db.execute("UPDATE notices SET status='cancelled',payload='{}' WHERE id=?", (row["id"],))
                    summary["cancelled"] += 1
                    continue
                # An explicit external flag is required before loading a custom transport.
                if settings.get("plugin", "local-json") != "local-json" and not allow_external:
                    summary["deferred"] += 1
                    continue
                external_requested = settings.get("plugin", "local-json") != "local-json"
                if external_requested and not notification_allowed(profile, notice["source_id"], notice["metric"], now, external=True):
                    summary["deferred"] += 1
                    continue
                if external_requested and settings.get("recipient_user_id") != profile["user_id"]:
                    raise ValueError("external recipient binding must match the profile user")
                recent = [s for s in sent if parse_timestamp(s["sent_at"]) > now - timedelta(days=7)]
                if len(recent) >= budget or any(s["stream_key"] == row["stream_key"] for s in recent):
                    summary["deferred"] += 1
                    continue
                if preferences.get("push_hours") is not None:
                    if now.astimezone(ZoneInfo(profile.get("timezone", "Asia/Shanghai"))).hour not in preferences["push_hours"]:
                        summary["deferred"] += 1
                        continue
                try:
                    plugin = plugin or get_delivery(settings.get("plugin", "local-json"))
                    if plugin.external and not allow_external:
                        raise ValueError("external delivery disabled")
                    receipt = plugin.send(notice, settings)
                    if not isinstance(receipt, str) or not receipt:
                        raise ValueError("delivery requires a nonempty acknowledgement")
                except DeliveryUncertain as exc:
                    self.db.execute("UPDATE notices SET status='uncertain',attempts=attempts+1,sent_at=?,error_type=? WHERE id=?", (now.isoformat(), type(exc).__name__, row["id"]))
                    sent.append({"stream_key": row["stream_key"], "sent_at": now.isoformat()})
                    summary["uncertain"] += 1
                    continue
                except Exception as exc:
                    self.db.execute("UPDATE notices SET status='failed',attempts=attempts+1,error_type=? WHERE id=?", (type(exc).__name__, row["id"]))
                    summary["failed"] += 1
                    continue
                self.db.execute("UPDATE notices SET status='sent',attempts=attempts+1,sent_at=?,receipt=?,error_type=NULL WHERE id=?",
                                (now.isoformat(), receipt, row["id"]))
                sent.append({"stream_key": row["stream_key"], "sent_at": now.isoformat()})
                summary["sent"] += 1
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return summary

    def forget_user(self, user_id: str) -> None:
        """Purge local ledger/feedback; external exports and providers are separate."""
        with self.db:
            self.db.execute("DELETE FROM feedback WHERE user_id=?", (user_id,))
            self.db.execute("DELETE FROM notices WHERE user_id=?", (user_id,))
