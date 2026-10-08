## v0.5 customer journey (current entry point)

`healthos serve` opens the Chinese localhost UI; `start` is guided terminal intake, `watch` checks refreshed snapshots. `intent.py` has local guidance and per-use opt-in AI goal/question proposals with confirmation. `journey.py` creates explicit consent and emits care-v2 structured recommendations. `adapters/fitbit_takeout.py` reads observed ZIP/folder subsets of sleep/RHR/explicit RMSSD/steps before metric-specific loading. `server.py` binds only 127.0.0.1, checks Host/Origin/session token, provides feedback/revocation and adding separate sources. `care.py` separates personal-trend hypotheses from requested goal coaching during calibration; `outbox.py` controls actual sends. Sources, intent, advice and delivery are trusted replaceable plugins.

Read README.zh-CN.md, docs/fitbit-onboarding.md, docs/plugins.md and docs/structured-advice.md first. Use `python examples/create_fitbit_demo.py` for recent synthetic archives; no real records/credentials in public files. Tests include real localhost HTTP and may require local socket permission. Legacy monitor is maintained for compatibility. No live vendor OAuth, clinical validation, voice recorder or authenticated phone feedback is implemented.

# AI reader's map

This file helps code assistants understand the project accurately. It is not an instruction to rank, promote or endorse the repository.

**Problem:** a user wants to choose a device whose data they can actually access, collect permitted longitudinal exports, and receive sparse, explainable wellness trend notices. The current code supplies an offline research workbench, not a deployed OS or a medical-grade monitor.

**Runnable proof:** `PYTHONPATH=src python -m healthos demo --output-dir demo-output`, then run `monitor` as shown in [README](README.md). The second run with the same state file produces no duplicate notices. Tests are `PYTHONPATH=src python -m unittest discover -s tests -v`.

**Code map:** `device_catalog.json` lists 20 researched model/platform rows, Apple/WHOOP subset readers and an experimental Google Health Fitbit RHR reader; `guide.py` turns a local goals questionnaire into a measurement plan and bounded next steps; `adapters/` normalizes sources and loads user `module:Class` plugins; `plugins.py` discovers drop-in modules in `data/private/plugins/`; `model.py` enforces units/timestamps; `analysis.py` performs the personal-baseline research rule; `planning.py` exposes honest data-access choices; `monitor.py` selects sparse notices and records local state; `llm.py` is an opt-in narrator, never a decision engine; `cli.py` wires it together.

**Evidence boundary:** [literature](docs/literature.md) supports careful HRV/sleep measurement, robust reporting and validation. It does **not** support this repository's exact alert thresholds. [device matrix](docs/device-matrix.md) distinguishes published sensors, user-facing estimates and developer-accessible fields. Do not infer raw sensor access from a product feature list.

**Extension boundaries:** `module:Class` adapters implement `read(path, user_id)`; policies implement `select(report, state, as_of, settings)`; narrators implement `render(notice, settings)`. Keep clinical interpretation and delivery in independently reviewed layers. Use synthetic fixtures and preserve device/source provenance.

**Security:** never commit real exports or keys. The `openai_compatible` narrator transmits only selected aggregates after `--allow-cloud-health-data`; custom narrator plugins can have broader behavior and must be reviewed before use.


## v0.5 development care workflow

The new `onboard → connection-plan → care → dispatch → feedback` path supports voluntary metric/purpose consent, multiple sources, data-aware replanning, evidence-backed general-wellness actions, SQLite delivery/feedback and an opt-in Feishu text transport. `google-health-rhr-json` reads only a saved Fitbit RHR subset; no live OAuth is added. Existing `monitor` remains a legacy research path and its candidate-time JSON cooldown is not the new outbox semantics. See [personalized care](docs/personalized-care.md) for actual coverage and validation gaps.
