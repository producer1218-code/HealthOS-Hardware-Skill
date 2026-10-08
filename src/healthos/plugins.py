"""Drop-in plugin discovery for user-supplied adapters, policies and transports.

A plugin is *trusted* Python, not a sandbox: it runs with the same privileges as
the application and can read anything the user can. Inspect a third-party plugin
before pointing it at real health records.

Users extend the four replaceable boundaries ([docs/plugins.md]) by dropping a
module into the plugin directory and referencing it as ``module:Class`` in a
source, advice or delivery setting:

    data/private/plugins/my_adapter.py  ->  "adapter": "my_adapter:MyAdapter"

Set ``HEALTHOS_PLUGIN_PATH`` (``os.pathsep``-separated) to point at a directory
outside the workspace. Entries are searched before the built-in adapters only if
they share a name, so prefix your module with something unique.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_VAR = "HEALTHOS_PLUGIN_PATH"
DEFAULT_DIR = Path("data/private/plugins")


def plugin_dirs() -> list[Path]:
    """Existing plugin directories, highest precedence first."""
    raw = os.environ.get(ENV_VAR, "")
    candidates = [Path(entry).expanduser() for entry in raw.split(os.pathsep) if entry.strip()]
    candidates.append(DEFAULT_DIR)
    seen: set[str] = set()
    found: list[Path] = []
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_dir():
            found.append(path)
    return found


def ensure_plugin_path() -> list[str]:
    """Make plugin directories importable. Idempotent; returns the entries added."""
    added: list[str] = []
    for directory in plugin_dirs():
        entry = str(directory)
        if entry not in sys.path:
            sys.path.insert(0, entry)
            added.append(entry)
    return added


def discover() -> list[dict]:
    """List importable modules and packages found in the plugin directories."""
    modules: list[dict] = []
    for directory in plugin_dirs():
        for child in sorted(directory.iterdir()):
            if child.is_dir() and (child / "__init__.py").is_file():
                modules.append({"module": child.name, "path": str(child / "__init__.py"),
                                "directory": str(directory)})
            elif child.suffix == ".py" and not child.name.startswith("_"):
                modules.append({"module": child.stem, "path": str(child),
                                "directory": str(directory)})
    return modules
