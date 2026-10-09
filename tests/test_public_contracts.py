"""Check published integration claims and agent interchange against actual runtime data."""
from copy import deepcopy
import importlib.util
import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from healthos.permissions import PATHS
from healthos.reports import cloud_packet

ROOT = Path(__file__).resolve().parents[1]


class PublicCapabilityTests(unittest.TestCase):
    def test_published_adapter_fields_match_runtime(self):
        manifest = json.loads((ROOT / "healthos-skill.json").read_text(encoding="utf-8"))
        published = {row["id"]: set(row["metrics"]) for row in manifest["data_adapters"]}
        self.assertEqual(published, {name: fields for name, (fields, _) in PATHS.items()})
        for entry in manifest["entrypoints"].values():
            self.assertTrue((ROOT / entry).is_file(), entry)
        self.assertFalse(manifest["mcp_server"])
        self.assertFalse(manifest["clinical_validation"])

    def test_public_site_bundle_contains_only_allowlisted_files(self):
        spec = spec_from_file_location("healthos_public_site", ROOT / "scripts/build_public_site.py")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        with TemporaryDirectory() as directory:
            work = Path(directory)
            module.build(work / "offline")
            self.assertEqual({p.name for p in (work / "offline").iterdir()},
                             {"index.html", ".nojekyll", "healthos-skill.json", "llms.txt"})
            module.build(work / "hosted", "https://example.test/healthos")
            html = (work / "hosted/index.html").read_text(encoding="utf-8")
            self.assertIn('<link rel="canonical" href="https://example.test/healthos/">', html)
            self.assertIn("https://example.test/healthos/", (work / "hosted/sitemap.xml").read_text())
            self.assertNotIn("oauth.json", " ".join(p.name for p in (work / "hosted").iterdir()))
            for unsafe in ["http://example.test", "https://user:secret@example.test", "https://example.test/?token=secret"]:
                with self.assertRaises(ValueError):
                    module.build(work / "unsafe", unsafe)
            with self.assertRaises(ValueError):
                module.build(work / "offline")


@unittest.skipUnless(importlib.util.find_spec("jsonschema"), "install the dev extra for public-schema validation")
class PublicSchemaTests(unittest.TestCase):
    def setUp(self):
        from jsonschema import Draft202012Validator, FormatChecker
        schema = json.loads((ROOT / "schemas/agent-context-v1.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.packet = json.loads((ROOT / "examples/agent_packet.synthetic.json").read_text(encoding="utf-8"))

    def test_runtime_generated_pair_and_cloud_boundary(self):
        self.validator.validate(self.packet)
        report = json.loads((ROOT / "examples/wellness_report.synthetic.json").read_text(encoding="utf-8"))
        self.assertEqual(self.packet["as_of"], report["as_of"])
        self.assertEqual(self.packet["period_summary"], report["metrics"])
        aggregate = cloud_packet(self.packet)
        for private_value in ["demo-user", "demo-device", self.packet["memory"]["user_stated_concern"], self.packet["as_of"]]:
            self.assertNotIn(private_value, json.dumps(aggregate))
        self.assertEqual(aggregate["schema_version"], "report-aggregate-v1")

    def test_rejects_wrong_version_impossible_days_and_missing_provenance(self):
        variants = []
        item = deepcopy(self.packet); item["schema_version"] = "unknown-v99"; variants.append(item)
        item = deepcopy(self.packet); item["period_summary"][0]["valid_days"] = 8; variants.append(item)
        item = deepcopy(self.packet); del item["period_summary"][0]["device_id"]; variants.append(item)
        item = deepcopy(self.packet); item["as_of"] = "not-a-date"; variants.append(item)
        for invalid in variants:
            self.assertTrue(list(self.validator.iter_errors(invalid)))


if __name__ == "__main__":
    unittest.main()
