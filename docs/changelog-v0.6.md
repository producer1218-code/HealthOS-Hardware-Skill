# v0.6 development: the wearable-to-personal-agent journey

User problem: a Fitbit Air owner cannot interpret their app or tell how data reaches an agent. The repository now guides access qualification, field consent, optional model setup, periodic reporting and personal feedback as one journey.

Added:
- Experimental Google Health v4 OAuth/read-only connector using official libraries. RHR, daily RMSSD and processed main sleep; account verification, minimal scopes, pagination, provenance/conflict checks, encrypted-storage confirmation.
- Periodic source-backed Markdown/JSON reports independent of anomaly notices. Separate report ledger and stable-ID deduplication.
- Replaceable aggregate-only report model with explicit sharing, recipient disclosure and local fallback.
- Private agent-context packet, inspectable memory and reset controls.
- Readable Chinese report UI and downloads; tutorials, methodology map, synthetic report and screenshot.
- Feishu send_report contract; no actual external message was sent during development.

Validation: 89 tests passed in the isolated environment with the Google extra installed; core regression, synthetic adapter/report/consent/privacy tests and official OAuth library integration tests. Local browser verification used synthetic data. Real Fitbit Air OAuth, external LLM quality, real Feishu delivery and clinical benefit remain unverified.

The live connector does not imply Google project eligibility. New-project onboarding is paused as checked 2026-10-09. The application relies on user-confirmed OS-encrypted storage rather than providing encryption itself.
