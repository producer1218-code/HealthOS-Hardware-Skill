# Adapter contract

An adapter reads a local file and yields canonical `Observation` values. Vendor authentication and data acquisition can be performed in a separate private service. The open core only requires:

```python
from pathlib import Path
from collections.abc import Iterable
from healthos.model import Observation

class MyAdapter:
    def read(self, path: Path, user_id: str) -> Iterable[Observation]:
        ...
```

Invoke an importable adapter as `python -m healthos ingest --adapter my_package.adapter:MyAdapter --input file --user pseudonym --output normalized.jsonl`. The included [custom adapter](../examples/custom_adapter.py) parses a synthetic sensor file and can be run with `--adapter examples.custom_adapter:ExampleSensorAdapter` while the repository root is on `PYTHONPATH`.

Before merging an adapter, verify:

1. Device model, firmware and app/API version.
2. Which fields are measured, vendor-derived or user-entered.
3. Original unit and conversion, time zone, sampling window and whether values are interval or daily totals.
4. Missing data, wear detection, quality and duplicate records.
5. OAuth scope or data-export permission, rate limits, deletion, and commercial reuse terms.
6. Synthetic tests for ordinary data, missing fields, unit changes and version changes.

Do not merge a connector that depends on scraped private endpoints, stored personal tokens or a proprietary SDK copied into this repository. If a vendor only offers computed scores, label the adapter accordingly and keep those scores outside the physiological vocabulary until separately modeled.

## Adapter status as of 2026-10-08

| Adapter | Status | Scope |
| --- | --- | --- |
| `csv` | Working | Documented canonical columns |
| `apple-health-xml` | Working, narrow | Selected quantity Records from a user export; no sleep or step interval aggregation |
| `whoop-v2-json` | Working, offline | Locally saved recovery/sleep response payloads; no OAuth client or paging |
| `jsonl` | Working | Canonical observations, including the synthetic demo output |
| `fitbit-takeout` | Working, observed export subsets | ZIP/folder: sleep, RHR, explicit RMSSD, interval steps; separate origins and declared devices; see [format contract](fitbit-onboarding.md) |
| `google-health-rhr-json` | Legacy offline subset | Saved dailyRestingHeartRate response; no OAuth or live sync |
| Huawei / Xiaomi / Zepp | Research only | Public developer documentation exists; approval and device-specific fields must be checked |
| OPPO / vivo | Research only | No generic direct health-data reader is claimed here |

The daily workflow is documented in [architecture](architecture.md). A policy plugin implements `select(report, state, as_of, settings)` and a narrator plugin implements `render(notice, settings)`; see `examples/custom_policy.py` and `examples/custom_narrator.py`. They can be selected with `module:Class` in the JSON configuration. Custom plugin code is executable Python and should be reviewed before using real data.
