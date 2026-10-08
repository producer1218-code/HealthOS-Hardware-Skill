"""Adapter registration. Third parties may pass `module:Class` to the CLI."""
from __future__ import annotations

from importlib import import_module
from typing import Protocol, Iterable
from pathlib import Path

from healthos.model import Observation


class Adapter(Protocol):
    def read(self, path: Path, user_id: str) -> Iterable[Observation]: ...


def get_adapter(name: str) -> Adapter:
    from .apple_export import AppleHealthExport
    from .canonical_csv import CanonicalCSV
    from .jsonl import JsonlAdapter
    from .whoop_json import WhoopV2JSON
    from .google_health_rhr import GoogleHealthRestingHeartRate
    from .fitbit_takeout import FitbitTakeout

    builtins = {"csv": CanonicalCSV, "apple-health-xml": AppleHealthExport,
                "whoop-v2-json": WhoopV2JSON, "jsonl": JsonlAdapter,
                "google-health-rhr-json": GoogleHealthRestingHeartRate,
                "fitbit-takeout": FitbitTakeout}
    if name in builtins:
        return builtins[name]()
    if ":" not in name:
        raise ValueError(f"unknown adapter: {name}")
    module_name, class_name = name.split(":", 1)
    cls = getattr(import_module(module_name), class_name)
    instance = cls()
    if not callable(getattr(instance, "read", None)):
        raise TypeError("adapter must implement read(path, user_id)")
    return instance
