"""User plugin drop-in discovery: directories, CLI listing and module:Class loading."""
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from healthos import cli, plugins
from healthos.adapters import BUILTIN_ADAPTERS, get_adapter

SAMPLE = '''\
import json
from pathlib import Path

from healthos.model import Observation


class DropInAdapter:
    def read(self, path: Path, user_id: str):
        for row in json.loads(path.read_text(encoding="utf-8")):
            yield Observation(user_id=user_id, timestamp=row["time"],
                              metric="resting_heart_rate_bpm", value=float(row["hr"]),
                              unit="bpm", source="drop-in", device_id="drop-in-1")
'''


class PluginTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        (self.dir / "my_sensor.py").write_text(SAMPLE, encoding="utf-8")
        (self.dir / "pkg").mkdir()
        (self.dir / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (self.dir / "_private.py").write_text("SIDE_EFFECT = 1", encoding="utf-8")
        self._env = mock.patch.dict(os.environ, {plugins.ENV_VAR: str(self.dir)})
        self._env.start()
        self._saved_path = list(sys.path)

    def tearDown(self):
        self._env.stop()
        sys.path[:] = self._saved_path
        sys.modules.pop("my_sensor", None)
        sys.modules.pop("pkg", None)
        self._tmp.cleanup()

    def test_plugin_dirs_honour_the_env_var(self):
        self.assertEqual(plugins.plugin_dirs()[0], self.dir)

    def test_ensure_plugin_path_is_idempotent(self):
        self.assertEqual(len(plugins.ensure_plugin_path()), 1)
        self.assertEqual(plugins.ensure_plugin_path(), [])

    def test_discover_lists_modules_and_packages_but_not_private_files(self):
        found = {item["module"] for item in plugins.discover()}
        self.assertLessEqual({"my_sensor", "pkg"}, found)
        self.assertNotIn("_private", found)

    def test_custom_adapter_loads_from_the_plugin_directory(self):
        adapter = get_adapter("my_sensor:DropInAdapter")
        self.assertTrue(callable(adapter.read))

    def test_builtin_names_are_stable_and_unknown_names_fail(self):
        self.assertIn("fitbit-takeout", BUILTIN_ADAPTERS)
        with self.assertRaises(ValueError):
            get_adapter("not-an-adapter")

    def test_plugins_command_reports_directories_and_modules(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            cli.main(["plugins"])
        payload = json.loads(buffer.getvalue())
        self.assertIn("my_sensor", {item["module"] for item in payload["discovered_modules"]})
        self.assertIn(str(self.dir), payload["active_plugin_dirs"])
        self.assertEqual(payload["custom_adapter_syntax"], "module:Class")
        self.assertIn("fitbit-takeout", payload["bundled_adapters"])


if __name__ == "__main__":
    unittest.main()
