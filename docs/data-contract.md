# Canonical data contract

One JSON Lines object per observation. `schema_version` belongs to the report, currently `1.0`. Required observation fields:

| Field | Meaning |
| --- | --- |
| `user_id` | Pseudonymous local ID; never an email or phone number |
| `timestamp` | ISO 8601 timestamp with a timezone offset; its local date is used in this prototype |
| `metric` | Name from `healthos.model.METRICS` |
| `value`, `unit` | Finite number and exact canonical unit |
| `source`, `device_id` | Provenance; a source/device change gets a separate baseline |
| `quality` | 0–1 **input integrity flag**, default 1 when an export gives no flag; not a claim of sensor accuracy |
| `context` | Optional short origin note; not interpreted by the baseline algorithm |

Supported metrics: `resting_heart_rate_bpm`, `heart_rate_bpm`, `hrv_rmssd_ms`, `hrv_sdnn_ms`, `sleep_minutes`, `steps_count`, `spo2_pct`, `skin_temp_c`, `respiratory_rate_bpm`, `self_report_energy_0_10`.

For CSV, the same fields become columns, except `user_id` is provided on the command line. `steps_count` means an already computed **cumulative daily total**; repeated values on one date use the maximum. Never feed interval step increments into it. Other duplicate daily readings use a median, which is a simple prototype rule rather than a measure-specific clinical aggregation.

HRV RMSSD and SDNN remain distinct because their calculations and collection windows differ. Skin temperature means wearable skin/wrist temperature, not core body temperature. `quality=1` on an Apple or WHOOP export means structurally usable export data; it does not certify sensor signal quality. Vendor scores such as Recovery or Readiness are deliberately not normalized into physiological metrics.

Outputs are stored locally. The CLI never uploads observations. Treat exports and reports as sensitive health data when deploying a consumer product.
