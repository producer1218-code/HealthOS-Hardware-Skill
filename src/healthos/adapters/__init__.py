"""Adapter registration. Third parties may pass `module:Class` to the CLI.

A custom adapter may live in the user plugin directory (see
:mod:`healthos.plugins`) instead of an installed package.
"""
from __future__ import annotations

from importlib import import_module
from typing import Protocol, Iterable
from pathlib import Path

from healthos.model import Observation


class Adapter(Protocol):
    def read(self, path: Path, user_id: str) -> Iterable[Observation]: ...


BUILTIN_ADAPTERS = (
    "fitbit-takeout",
    "csv",
    "apple-health-xml",
    "whoop-v2-json",
    "jsonl",
    "google-health-rhr-json",
    "google-health-json",
    "google-health-api",
)


def builtin_adapters() -> dict:
    """Instantiable built-ins, imported lazily to keep startup cheap."""
    from .apple_export import AppleHealthExport
    from .canonical_csv import CanonicalCSV
    from .jsonl import JsonlAdapter
    from .whoop_json import WhoopV2JSON
    from .google_health_rhr import GoogleHealthRestingHeartRate
    from .fitbit_takeout import FitbitTakeout
    from healthos.google_health import GoogleHealthAPI, GoogleHealthSnapshot

    return {"csv": CanonicalCSV, "apple-health-xml": AppleHealthExport,
            "whoop-v2-json": WhoopV2JSON, "jsonl": JsonlAdapter,
            "google-health-rhr-json": GoogleHealthRestingHeartRate,
            "fitbit-takeout": FitbitTakeout, "google-health-json": GoogleHealthSnapshot, "google-health-api": GoogleHealthAPI}


def get_adapter(name: str) -> Adapter:
    builtins = builtin_adapters()
    if name in builtins:
        return builtins[name]()
    if ":" not in name:
        raise ValueError(f"unknown adapter: {name}")
    from healthos.plugins import ensure_plugin_path
    ensure_plugin_path()
    module_name, class_name = name.split(":", 1)
    cls = getattr(import_module(module_name), class_name)
    instance = cls()
    if not callable(getattr(instance, "read", None)):
        raise TypeError("adapter must implement read(path, user_id)")
    return instance
