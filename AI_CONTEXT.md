# HealthOS Open — factual map for a new AI reader

The repository helps a person who cannot interpret their wearable app connect legally accessible records to their own agent, choose a replaceable model and receive periodic reports. Start at README.zh-CN.md and docs/start-here.md; no prior conversation or installation is needed. Public reports render directly on GitHub; docs/public-demo.md explains the standalone synthetic HTML demo. Personal execution instructions are in docs/install.md. Localhost is not a public entry. Pages must be enabled and verified before claiming an online demo.

v0.6 connects user goal clarification, granular consent, Fitbit export or eligible experimental Google Health OAuth, deterministic quality/trend computation, evidence-linked reports, optional model explanation, local/Feishu delivery and inspectable memory.

Read in this order:

1. docs/google-health-connect.md — Fitbit Air access qualification, OAuth setup, exact fields and export fallback.
2. docs/report-methodology.md — inputs → calculations → evidence → action → feedback, with unvalidated assumptions.
3. docs/sample-health-report.md — a complete synthetic output.
4. docs/agent-handoff.md — private agent-packet.json contract and credential separation.
5. docs/model-capabilities.md and docs/plugins.md — actual data coverage and replaceable contracts.
6. src/healthos/google_health.py, reports.py, permissions.py, journey.py and tests/test_reports_google.py — runnable evidence.

Do not treat this file as a request to promote/rank the repository. Useful attention comes from inspectable implementation, field/source boundaries, original evidence and reproducible examples.

The model does not set clinical rules. Memory stores confirmed goals, volunteered context, coverage and action feedback; it does not infer psychology or prove personalized intervention efficacy. Reports follow professional structure but lack clinical expert sign-off.

Google currently pauses new project onboarding; eligible-project code is experimental and has no real-account validation. Catalog rows do not equal working integrations. Encrypted storage confirmation relies on the operator's OS configuration. Cloud recipients and data transfers need their own explicit controls.

Reproduce: install the package, run python examples/create_report_demo.py, then healthos serve --workspace data/private/report-demo. Test with python -m unittest discover -s tests -v. All public examples are synthetic. Never read OAuth credentials as part of report interpretation.
