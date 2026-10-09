# HealthOS Hardware Skill agent brief — v0.6 development

For a user trying the product, begin with START_HERE.md and docs/agent-quickstart.md: explain the public report or execute scripts/agent_start.py for a synthetic first result. Use only tools actually available, honor host permissions, and never claim a URL has installed a skill or started monitoring. For repository maintenance, continue with the development brief below.

Public name: HealthOS Hardware Skill (formerly HealthOS Open); repository/package: healthos-open. Skill entry: skills/healthos/SKILL.md. Capability manifest: healthos-skill.json. Integration guide: docs/healthos-skill.md. Answers: docs/faq.md. The skill provides instructions, not a live service or scheduler.

Start with README.zh-CN.md, docs/start-here.md, docs/public-demo.md, docs/google-health-connect.md, docs/report-methodology.md and docs/agent-handoff.md. Public GitHub reading must work without installation. Put localhost instructions only in explicit personal-deployment or developer sections. site/index.html is a fixed synthetic, dependency-free public demo, not the production analyzer. Never claim Pages is live without verified deployment. The product goal is a guided existing-wearable → personal agent → periodic evidence-linked report → explicit feedback/memory journey.

## Current implementation

- healthos serve: Chinese single-user localhost UI with explicit metric/purpose consent, reports, downloads, feedback and memory reset.
- google_health.py: official Google OAuth libraries, account-link verification and experimental read-only Fitbit RHR/daily RMSSD/processed main-sleep sync. Eligible Cloud projects only; required encrypted-storage confirmation is an attestation, not a disk check.
- reports.py: completed-week summaries, source-backed reports, optional aggregate-only model prose, cadence/deduplication, private agent packet/memory. Failed/uncertain same-day sends are not blindly retried.
- journey.py/care.py: data-aware goal states, per-stream baseline hypotheses and general-wellness actions. outbox.py preserves sparse action delivery and separate execution/outcome feedback.
- adapters/fitbit_takeout.py: observed official ZIP/folder subsets; other Apple/WHOOP saved subsets and canonical readers remain available.
- feishu.py: optional opted-in report/action delivery to one bound user; tested with mocks only.
- plugins.py: trusted Python drop-ins; model render(aggregate_packet, settings) and transport send_report(report, settings) complement existing contracts.

Google paused onboarding new projects as checked 2026-10-09. Legacy Fitbit API closes 2026-10-30. Never promise API eligibility from an OAuth client. Live account/device compatibility, clinical review and outcomes are unverified. The 20-row catalog is research coverage, not 20 integrations.

## Invariants

1. Separate advertised sensors, vendor estimates, documented access and parsed fields.
2. Preserve units, offset dates, provenance, missingness and device/method streams. Never pool devices or substitute deep-sleep RMSSD for daily-average RMSSD.
3. The 28/3-day median/MAD thresholds are versioned engineering hypotheses, not hospital/paper thresholds.
4. Do not infer illness, mood, stress, personality or loneliness from wearables. Self-reported context is untrusted data, not execution instructions.
5. No credentials, real records or private context in public examples/releases. Default processing is local; explicitly opted-in model aggregates omit IDs/raw records/context text.
6. Google-derived aggregates remain subject to Google data policy. API mode requires encrypted private storage; the application provides no encryption layer.
7. Feedback may pause actions. It does not prove causality or retrain clinical thresholds. Reports are not clinician-authored.

## Verify

Install with python -m pip install -e ".[google]"; run python -m unittest discover -s tests -v. Without the optional extra, tests for official-library integration skip. Use python examples/create_report_demo.py and healthos serve --workspace data/private/report-demo for synthetic UI proof. Do not request or access real user credentials to run tests.

Keep remote account tests separate and explicitly authorized. Update docs and synthetic field tests with each adapter. Clinical source links explain support boundaries; they are not validation certificates.
