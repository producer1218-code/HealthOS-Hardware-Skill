# v0.6 Google/API and report storage

Google API health records and tokens must be encrypted at rest under its [user data policy](https://developers.google.com/health/policies/health-api-developer-user-data-policy). connect-google refuses to start without explicit encrypted-storage confirmation. This is an operator attestation, not verification or application encryption: keep the client JSON, entire private workspace, snapshots, SQLite databases and reports on OS-encrypted storage. Credential file permissions alone are insufficient. Tokens remain in connection/oauth.json for the connector only.

API-derived aggregates are still governed by Google sharing restrictions. Report models are default-off and receive allowlisted aggregates only after explicit sharing; endpoint recipient is shown locally. Custom Python plugins are trusted, not sandboxed. Full agent packets contain private identifiers/context and require separate sharing consent when handed to a cloud agent.

forget-memory removes generated local report history, feedback and volunteered answers, preserving source files, goals, connection credentials and action delivery deduplication. To disconnect Google, revoke the app in Google account connections and remove the private connection separately. External sent copies and exports require separate deletion. This prototype is not an audited hosted service or a medical record security platform.

# Security and sensitive data

The current app is single-user and local. `serve` binds 127.0.0.1 only, validates Host/Origin, requires a per-process token for mutations and does not serve uploaded raw files. Do not proxy it to the internet; no account authentication or multi-user isolation is implemented. Private files are not encrypted by the application.

Store exports, uploads, profiles, outputs, SQLite and transport configuration under `data/private/`, never in tracked examples. A ZIP upload makes a local copy before analysis consent. Fitbit reads only authorized supported metric files; legacy generic readers may read the entire selected file before filtering. Custom plugins execute trusted Python, not sandboxed code: inspect them before giving access to health data.

Local analysis, proactive notices and external summary delivery are separate purposes, checked before reads and again before sends. Revocation cancels queued notices on the next pass; it does not delete original exports, sent local files or third-party copies. `forget` erases only local outbox/feedback records for that user.

Opt-in intent AI transmits only volunteered request text to a configured HTTPS provider, with user confirmation before goals become active. This text can itself be sensitive. Keys are environment variables, not JSON values. The legacy monitor narrator has separate explicit aggregate-sharing opt-in. Feishu delivery requires a matching recipient, per-metric external consent and the command allow flag. Ambiguous delivery pauses retries for reconciliation. No authenticated Feishu feedback callback is deployed.

Never log raw health records or API tokens. Public examples and tests are synthetic. Report vulnerabilities privately to the maintainer at 1626952981@qq.com; do not post personal exports or credentials in issues. Production hosting needs authentication, OAuth scope audits, encryption, retention/deletion controls, incident handling and independent review.
