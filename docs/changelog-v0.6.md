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

Public visitor entry correction (2026-10-09): README is now a no-install tour with GitHub-rendered reports and clear capability links. Personal startup instructions moved to docs/install.md. Added guided visitor documentation, dependency-free standalone synthetic HTML, and a Pages workflow that packages the public site but deploys only after initial administrator enablement. Browser checks cover insufficient records, unimplemented Apple sleep fields, unsupported brands, feedback pause/reset and cadence. No live-site claim is made before deployment.

HealthOS Skill identity and discoverability (2026-10-09): retain healthos-open repository/package URL; add an actual Agent Skills folder, factual FAQ, capability manifest generated from the permission registry, a checked agent-context-v1 serialization schema, paired synthetic production-function examples, crawlable initial HTML and matching SoftwareSourceCode metadata. Public site bundle and configured canonical/sitemap remain gated on Pages enablement. Suggested About/Topics are prepared but not applied through the connector. No index/ranking/recommendation or cross-host behavior guarantee.

Agent first experience (2026-10-09): add START_HERE.md with routes for URL-reading, file/Python and Skill hosts; one-command source execution generates a production-function synthetic report, matched Agent packet and explicit receipt. No HealthOS package installation or LLM key is needed for the first run; Python and timezone data must already be available. Existing directories are never overwritten. A public MCP endpoint, real-device authorization and always-on hosting are not supplied by this entry. Tests include isolated-process execution, paired report consistency and existing-private-workspace preservation.

Public name update (2026-10-09): rename the current public identity to HealthOS Hardware Skill across entrypoints, Skill display metadata, capability exporter, citation and public HTML. Retain historical aliases and the healthos-open repository/package URL. Runtime behavior is unchanged.

Methodology-first entry (2026-10-10): reposition README and START_HERE for existing-agent users; begin with device and health question, then propose permitted observation plans. Add a self-contained Skill observation protocol, question/data/evidence mapping and optional proposal JSON (not imported by runtime). Synthetic execution becomes optional. Replace README screenshots with an image-generated consulting-style product proposition and use the verified renamed public repository URL. Runtime algorithms and connector support are unchanged.
