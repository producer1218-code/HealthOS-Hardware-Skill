# HealthOS Open

[![tests](https://github.com/producer1218-code/healthos-open/actions/workflows/tests.yml/badge.svg)](https://github.com/producer1218-code/healthos-open/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Turn the wearable you already own into a guided, personal health agent: connect permitted data, plug in your model, receive evidence-linked periodic reports, and refine the plan through feedback.**

v0.6 development: Chinese localhost onboarding, Fitbit exports, an experimental Google Health OAuth/read-only connector, periodic Markdown/JSON reports, replaceable LLM commentary, inspectable personal memory and optional Feishu delivery. Reports use professional observation structure and primary sources; they are not clinician-authored or clinically validated.

[中文完整指南](README.zh-CN.md) · [Fitbit Air / Google connection](docs/google-health-connect.md) · [Read a synthetic report](docs/sample-health-report.md) · [Methodology](docs/report-methodology.md) · [Bring your own agent](docs/agent-handoff.md)

## The journey

~~~text
My existing wearable + my goals
→ guided export or eligible OAuth access
→ explicit metric and purpose consent
→ source/device/method-specific quality and personal trends
→ periodic evidence-linked report + optional BYO-model explanation
→ local or opted-in phone delivery
→ execution and outcome feedback → inspectable personal memory
~~~

A Fitbit Air user can discover how their sleep, resting heart rate and HRV records become a useful report, instead of needing to interpret the vendor app. HealthOS explains access routes and fields before requesting permission.

**Access status, checked 2026-10-09:** [Google](https://developers.google.com/health) is currently not onboarding new Health API projects; the legacy Fitbit Web API shuts down on 2026-10-30. Creating an OAuth client does not grant project eligibility. Eligible users can try the experimental connector; others can start with official exports. Neither live Fitbit Air compatibility nor clinical benefit has been verified.

## Try a complete synthetic journey

Python 3.10+, with 3.12 recommended. Windows installs timezone data.

~~~bash
git clone https://github.com/producer1218-code/healthos-open.git
cd healthos-open
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows: .venv\Scripts\Activate.ps1
python -m pip install -e .
python examples/create_report_demo.py
healthos serve --workspace data/private/report-demo
~~~

Open http://127.0.0.1:8765. The demo makes no vendor, LLM or Feishu calls. Use a separate real-user workspace and grant its permissions explicitly.

## Connect real data

Run healthos serve using the default data/private/personal workspace. Confirm goals and voluntary context, select a source, select metrics, separately authorize analysis/notices/external delivery, and enable periodic reports.

| Route | Working fields | Status |
| --- | --- | --- |
| Fitbit ZIP/folder export | sleep duration, RHR, explicit RMSSD, steps | observed export subsets; refresh manually |
| Google Health API / saved v4 JSON | Fitbit daily RHR, daily-average RMSSD, processed main-sleep duration | experimental; eligible projects only; no live steps/SpO2/temperature |
| Apple Health XML | HR, RHR, SDNN, SpO2, sleeping wrist temperature | subset; no sleep duration or steps |
| Saved WHOOP v2 JSON | RHR, RMSSD, SpO2, skin temperature, sleep duration, respiratory rate | offline subset; user supplies authorized responses |
| CSV / JSONL / custom Python | explicit canonical metrics | user-mapped; no model validation implied |

The [20-row device catalog](docs/model-capabilities.md) is research coverage, not 20 validated integrations. Public estimates do not imply raw signal access. Provisional Google metadata cannot reliably distinguish two identical devices.

For eligible Google projects, follow the [step-by-step guide](docs/google-health-connect.md), including account linking, callback configuration, encrypted storage and consent:

~~~bash
python -m pip install -e ".[google]"
healthos connect-google --client data/private/personal/client.secrets.json --connection data/private/personal/google --metric sleep_minutes --metric resting_heart_rate_bpm --metric hrv_rmssd_ms --encrypted-storage-confirmed
~~~

Choose Google Health API in the UI and the absolute connection directory. The official Google OAuth libraries open the system browser. Google requires encrypted health data and tokens at rest: the connector requires explicit confirmation of OS-encrypted storage, but does not inspect or provide disk encryption.

## Plug in your LLM

Reports work without a model. Copy examples/report_settings_llm.json into your private workspace, configure endpoint/model/api_key_env, set your key in that environment variable, then:

~~~bash
healthos configure-reports --settings data/private/personal/report-settings.local.json --allow-cloud-report
healthos serve
~~~

A compatible Chat Completions JSON endpoint receives allowlisted aggregates, goal identifiers and feedback counts. No IDs, raw records, dates, paths, tokens or free-text context are sent by the bundled renderer. Other providers implement render(aggregate_packet, settings) as a trusted module:Class plugin. The page exposes the configured recipient and sharing control.

The model returns explanatory draft prose/questions; deterministic tables, evidence and actions remain intact. Schema and numerical checks are limited guards, not proof that prose is accurate. On model failure, the source-backed local report remains available. Google derived/aggregated records remain subject to its [user data policy](https://developers.google.com/health/policies/health-api-developer-user-data-policy).

## Reports, delivery and learning

The page offers 7/14/30-day delivery cadence. The first report appears on the next pass; later reports follow the previous analysis date. Each report describes the last seven completed dates, independent of delivery cadence. Keep serve or watch running on your computer; GitHub does not execute your private monitoring.

Default delivery writes reports/*.md and JSON and renders the report locally. An opted-in Feishu transport can send observations/actions to a bound recipient:

~~~bash
healthos serve --delivery-settings data/private/feishu_delivery.json --allow-external-delivery
~~~

[Feishu setup](docs/personalized-care.md#飞书设置). Free-text personal history stays local. Mocked transport tests do not establish a real-account send; phone feedback is not implemented. Periodic reports and sparse action reminders use separate ledgers. Stable IDs prevent duplicate reports; failed/uncertain same-day sends require inspection rather than blind retries.

Memory contains confirmed goals, volunteered context, coverage, execution/outcome counts and paused actions. Feedback updates action suitability, not clinical thresholds or causal conclusions. Review memory.json or use healthos forget-memory. This clears local generated reports/context/feedback while preserving exports, connections and goals; external copies need separate deletion.

Your own agent can use agent-packet.json under the [handoff contract](docs/agent-handoff.md), rather than reading credentials.

## Method and verification

Weekly statistics keep missing dates and separate sources/devices/methods. Personal trends use versioned 28/3-day median/MAD engineering hypotheses, with at least 14 baseline days. These parameters have not been clinically validated. CDC, HRV methodology and COM-B sources inform contextual questions and general-wellness actions; they do not validate the software or authorize diagnostic claims.

~~~bash
python -m unittest discover -s tests -v
healthos report
healthos watch --once
healthos plugins
~~~

See [report methodology](docs/report-methodology.md), [literature](docs/literature.md), [plugin contracts](docs/plugins.md), [security](SECURITY.md) and [validation](docs/validation.md). Tests use synthetic records, mocked network calls and real localhost HTTP. Live vendor accounts, actual hardware accuracy, human expert review and outcomes remain unverified.
