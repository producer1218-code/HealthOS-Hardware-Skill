# HealthOS Open

[![tests](https://github.com/producer1218-code/healthos-open/actions/workflows/tests.yml/badge.svg)](https://github.com/producer1218-code/healthos-open/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10 | 3.12](https://img.shields.io/badge/python-3.10%20%7C%203.12-blue.svg)](pyproject.toml)
[![Local-first](https://img.shields.io/badge/data-stays%20local%20by%20default-2ea44f.svg)](SECURITY.md)
[![No telemetry](https://img.shields.io/badge/telemetry-none-2ea44f.svg)](SECURITY.md)

**User goals + voluntary wearable data → explainable, proactive wellness actions.** v0.5 development: a local, single-user application with a complete Fitbit export journey, structured advice, feedback and pluggable delivery.

[中文完整指南](README.zh-CN.md) · [Fitbit import](docs/fitbit-onboarding.md) · [Feishu delivery](docs/personalized-care.md) · [Plugin contracts](docs/plugins.md) · [Output schema](docs/structured-advice.md)

`Fitbit export` · `wearable health data` · `local-first` · `privacy` · `consent` · `HRV / resting heart rate / sleep / steps trends` · `quantified self` · `personal health record` · `Python` · `no telemetry`

```text
Describe what matters → local guidance / opt-in AI proposal → confirm goals
→ choose existing hardware → consent to metrics and purposes
→ check actual coverage → device-specific trends / requested goal coaching
→ structured action → local or Feishu delivery → execution and outcome feedback
```

## Start

Python 3.10+ (3.12 recommended), no runtime dependencies on macOS/Linux; Windows installs timezone data. The interface currently uses Chinese; the CLI and schema use stable English identifiers.

```bash
git clone https://github.com/producer1218-code/healthos-open.git
cd healthos-open
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
healthos serve
```

Open `http://127.0.0.1:8765`. Describe your sleep, recovery or activity goal, confirm the proposed goals, answer optional questions, choose an export, then explicitly select metrics and purposes. Analysis, proactive notices and external delivery are separate, default-off permissions. No file yet? Save a waiting plan. Windows: use `py -3.12` and `.venv\Scripts\Activate.ps1`.

Fitbit users download an archive through [Google Takeout / the official account export route](https://support.google.com/googlehealth/answer/14236615). The reader supports observed subsets of sleep, resting heart rate, explicit RMSSD HRV and interval steps in ZIPs or folders. It preserves formats and origins, skips Apple-imported measurements in the Fitbit route and rejects conflicting records. It does not implement vendor OAuth. Export coverage varies; a user-declared device binding cannot identify multiple devices inside an inseparable archive.

## Try without an account

```bash
python examples/create_fitbit_demo.py
healthos serve --workspace data/private/synthetic-person
```

Select `data/private/synthetic-fitbit.zip` in the page. It contains recent, explicitly synthetic records. Confirm sleep/recovery goals and permissions to see evidence, feedback controls and downloadable JSON.

![Synthetic action and feedback](docs/synthetic-plan.png)

`healthos start` offers terminal guidance. `healthos watch --once` runs an existing private profile once; `watch` and `serve` check updated exports every hour by default. The default workspace is `data/private/personal`.

## Proactive delivery

Local JSON delivery works out of the box. Configure the optional Feishu application bot to receive summaries on your phone:

```bash
healthos serve --delivery-settings data/private/feishu_delivery.json --allow-external-delivery
```

Follow the [Feishu setup](docs/personalized-care.md#飞书设置), set credentials in environment variables, bind your own recipient, and opt in to external summary delivery in the page. Feishu sends text; feedback currently happens in the local page, not through authenticated phone callbacks. Transports have mocked tests, not a verified real-account send.

Exports are **snapshots**. A running process cannot invent new measurements: update the chosen directory/file, or reselect an uploaded ZIP. Do not run competing transports against the same queue without understanding delivery semantics.

## Advice, consent and learning boundaries

Personal-trend actions use separate device/source/method streams and versioned 28/3-day median/MAD rules, with at least 14 valid baseline days. These thresholds are **unvalidated engineering hypotheses**. Requested goal coaching can offer a general wellness action during calibration when a relevant recent record exists; it is explicitly not an anomaly finding. Missing or stale data do not trigger coaching.

Every action has evidence, its supported scope, a content version and a review status. Public sources do not imply clinician review. Execution and self-reported outcomes remain separate. Rejection or feeling worse pauses the action; feedback does not prove causality or retrain clinical thresholds. Successful-send budgets, cooldowns, consent rechecks, revocation and duplicate suppression constrain delivery. Ambiguous remote responses require reconciliation.

Default intent clarification is explicitly labeled local keyword guidance, not AI. An optional compatible AI sees only the volunteered request, with per-use opt-in, proposes goals/questions, and awaits user confirmation. It cannot grant consent or set clinical rules. Adapters, intent, advice and transports are replaceable trusted Python plugins; see [contracts](docs/plugins.md).

## Scope and verification

The full suite covers synthetic parsing, consent, calibration, freshness, HTTP onboarding, delivery, feedback and revocation; run:

```bash
python -m unittest discover -s tests -v
```

The UI journey was also exercised in a browser. Private exports and credentials are excluded from this repository. Store them in `data/private/`; revocation does not erase original files or already delivered copies. There is no application-layer encryption.

This is a local research tool for general wellness, not diagnosis, treatment or emergency monitoring. No clinician has reviewed the exact implementation or validated its health benefit. Apple XML coverage remains narrow and excludes sleep. The 20-model research catalog is not a claim of 20 working connectors. Voice, recordings, productivity alignment, production accounts and a mobile companion are future work. Legacy `monitor` is retained for research compatibility; new journeys use the consent-aware care/outbox flow.

[Evidence ledger](docs/evidence-to-code.md) · [Method](docs/method.md) · [Model inventory](docs/model-capabilities.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · MIT
