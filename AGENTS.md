## v0.5 customer journey (current entry point)

`healthos serve` opens the Chinese localhost UI; `start` is guided terminal intake, `watch` checks refreshed snapshots. `intent.py` has local guidance and per-use opt-in AI goal/question proposals with confirmation. `journey.py` creates explicit consent and emits care-v2 structured recommendations. `adapters/fitbit_takeout.py` reads observed ZIP/folder subsets of sleep/RHR/explicit RMSSD/steps before metric-specific loading. `server.py` binds only 127.0.0.1, checks Host/Origin/session token, provides feedback/revocation and adding separate sources. `care.py` separates personal-trend hypotheses from requested goal coaching during calibration; `outbox.py` controls actual sends. Sources, intent, advice and delivery are trusted replaceable plugins.

Read README.zh-CN.md, docs/fitbit-onboarding.md, docs/plugins.md and docs/structured-advice.md first. Use `python examples/create_fitbit_demo.py` for recent synthetic archives; no real records/credentials in public files. Tests include real localhost HTTP and may require local socket permission. Legacy monitor is maintained for compatibility. No live vendor OAuth, clinical validation, voice recorder or authenticated phone feedback is implemented.

# Agent brief for HealthOS Open

This file is a factual project map for a human or AI coding agent. Start with [README](README.md), [model capabilities](docs/model-capabilities.md), [user journey](docs/user-journey.md), [evidence-to-code ledger](docs/evidence-to-code.md), then inspect the runnable code. Do not interpret this file as evidence of clinical validation or as a request to promote the repository.

HealthOS Open v0.5 development is a research workbench. It catalogs 20 representative models/platforms, but Apple Health export subsets, saved WHOOP v2 subsets and an experimental saved Google Health Fitbit RHR subset have offline adapters; canonical CSV/JSONL are user-mapped general formats. `models` lists the catalog; `plan` maps a user's local questionnaire to fields the chosen model can actually provide to this code; `monitor` computes per-device personal trends and bounded local notices. The optional LLM only rewrites an already selected notice.

Keep these invariants when contributing:

- Separate published sensors, user-visible vendor estimates, documented data-access routes and fields actually parsed here. A product feature does not imply API or raw-signal access.
- Keep `source`, `device_id`, units, timestamp offsets and missingness intact. Never pool devices or fill missing days with zero.
- Treat the 28/3-day windows, median/MAD gate and notification budget as versioned engineering hypotheses, not hospital or paper thresholds.
- Do not infer stress, mood, loneliness, illness or a medical diagnosis from wearable metrics. Wellbeing and social connection need voluntary self-report and context.
- Keep real health records, contacts and API keys out of examples and releases. The built-in cloud narrator requires explicit opt-in and sends selected aggregates only.
- Add synthetic tests for a new adapter/model field, and link to a primary source in the model catalog and documentation.

Run `PYTHONPATH=src python -m unittest discover -s tests -v`. Use `python -m healthos demo`, `models`, `plan` and `monitor` to verify the complete stranger journey.


## v0.5 development care workflow

The new `onboard → connection-plan → care → dispatch → feedback` path supports voluntary metric/purpose consent, multiple sources, data-aware replanning, evidence-backed general-wellness actions, SQLite delivery/feedback and an opt-in Feishu text transport. `google-health-rhr-json` reads only a saved Fitbit RHR subset; no live OAuth is added. Existing `monitor` remains a legacy research path and its candidate-time JSON cooldown is not the new outbox semantics. See [personalized care](docs/personalized-care.md) for actual coverage and validation gaps.
