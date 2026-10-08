# Data access playbook: how an agent legitimately obtains someone's health data

Reviewed 2026-10-08. This is the operational companion to [device-matrix.md](device-matrix.md): the
matrix says *what* each vendor exposes, this page says *by which route* and *what it costs you in
permission, paperwork and engineering*. Nothing here authorizes a connection; each vendor's current
terms govern, and terms change without notice.

## The four access tiers

An agent must classify every intended data source into exactly one tier before writing code, because
the tier determines the permission model, the review burden and what may legally ship in an open
repository.

| Tier | Route | Vendor approval | What you actually receive | May ship in this repo |
| --- | --- | --- | --- | --- |
| A | User-initiated local export | None | Files the user downloads and hands you | Yes — adapter only |
| B | User-authorized OAuth API | App review, sometimes per-scope | Vendor-normalized records, rate-limited | Adapter that reads a saved response |
| C | Enterprise / partner API | Contract, fee, sometimes device procurement | All-day metrics, often higher resolution | No |
| D | Device-level BLE / SDK | Vendor SDK licence | Raw or high-frequency signals, device-dependent | No |

**Tier A is the backbone of this project.** It needs no vendor relationship, works for a single person
today, and is the only route where the open core can be complete. Tiers B–D are product decisions
that belong to a funded, contracted operator — a private service, not a public repository.

## Tier A — local export, no vendor approval

The user produces the file; the agent only parses it. This is the most under-used route in the
industry and the one this project optimizes for.

- **Apple Health:** the user runs *Export All Health Data* in the Health app and gets `export.xml`
  plus route files. Parse `Record` elements by `type`; each has `startDate`, `endDate`, `value` and a
  `sourceName` that identifies the originating device or app. `sourceName` is what makes device
  isolation possible — do not discard it, and do not assume it is stable across app updates.
- **Fitbit / Google:** check the account's current download or Takeout options and the actual JSON/CSV
  fields for the user's device and region before committing to a parser; these formats differ from APIs.
- **WHOOP:** confirm a currently available user export for that account; this repository parses only a
  locally saved, explicitly tagged v2 recovery/sleep API response, not arbitrary app exports.
- **Oura, RingConn, Samsung, Ultrahuman, Withings, Garmin and other rings/bands:** check current account
  export, documented partner permission or the user's platform sync (HealthKit / Health Connect),
  *field by field*. A product page does not prove export rights or that a sync preserves original device
  attribution. Unless a format and permission are verified, mark the route unverified; no parser is
  implemented here.
- **AI pendants and recorders:** these ship audio, transcript and sometimes a daily summary rather
  than physiological series. Treat them as a separate carrier class — see below.

Rules for Tier A work: never ask a user to send the file to a server if the parse can be local; never
commit the file; strip all directory names from any fixture; and record the export's own date in the
adapter output, because a stale export silently looks like missing data.

## Tier B — user-authorized OAuth APIs

The user consents, your registered application reads that user's data. Typical shape, which recurs
across vendors: register an app, receive a client ID and secret, run an authorization-code flow,
refresh a token, pull paginated JSON, respect rate limits, handle revocation.

- **Oura:** [Oura API V2](https://cloud.ouraring.com/v2/docs), OAuth2. A registered application starts
  with a **ten-user limit** and must be submitted for review before wider release, per the
  [getting-started page](https://cloud.ouraring.com/docs/). The v1 API was removed in January 2024 —
  do not build on anything still pointing at it.
- **WHOOP:** OAuth v2 with webhooks. The cloud API returns processed recovery, sleep and activity
  records; continuous heart rate is not part of it, and the vendor's own support pages say so.
- **Google / Fitbit:** the migration to the Google Health API means new projects are not currently
  being onboarded. Treat as blocked, not as broken.
- **Xiaomi, Huawei, Zepp:** official health-data documentation exists. Expect per-scope approval,
  region restrictions and device-specific field coverage; confirm field-by-field rather than trusting
  a platform overview page.
- **Garmin:** the [Connect Developer Program Health API](https://developer.garmin.com/gc-developer-program/health-api/)
  is documented as an enterprise offering with approval and an evaluation environment, and commercial
  use requires a licence fee.

Engineering pattern that keeps the open core honest: the acquisition service holds tokens and talks
to the network; it writes canonical JSON Lines; the open repository only consumes that file. This is
also the only way to test an adapter without credentials.

## Tier C — enterprise and partner programs

Contracts, fees, population-health agreements, sometimes supplied hardware. Useful for corporate
wellness, payer and clinical research contexts. Outputs are usually device-level metrics at higher
resolution and are frequently covered by terms that forbid redistribution of derived data — which is
exactly why none of it belongs in an MIT repository.

## Tier D — device-level BLE and vendor SDKs

Depending on the device, a vendor SDK can expose raw photoplethysmography, electrocardiogram or
motion streams. This is the only route to genuine signal-processing research, and it is also the most
fragile: SDK licences usually forbid publishing the SDK binary itself, firmware updates break parsing,
and the documentation is written per project rather than per product family.

Practical consequence: an open algorithm repository should contain *adapters for formats*, not
*dependencies on SDKs*. A contributor with an SDK under licence can run it privately and contribute
the normalized output schema, fixtures and tests — which is the part everyone else needs.

## The AI pendant and recorder class

Neck-worn and lapel AI wearables make different claims from watches. For example, the official
[Looki L1 product site](https://www.looki.ai/) describes a camera, microphones and motion sensors,
with lifelogs, automatic vlogs and reminders. This establishes *marketed context features*, not a
public export/API, measurement validity or permission to analyse third-party footage. Other recorder
brands vary. Do not assume these devices publish physiological series; mark export and API access
**unverified** until documented by the vendor.

The right architectural move is to accept them as **context carriers, not measurement carriers**. A
transcript-derived note such as "user reported a stressful week" belongs in the observation's
`context` field, not in a physiological metric, and must never be silently correlated with heart-rate
variability and then presented as cause. A recorder may suggest a question about *why* a change happened;
it cannot establish a cause or measure the change. If a context source includes bystanders,
first establish explicit consent, minimization and deletion rules; never ingest raw recordings by
default. Context ingestion is not implemented in this repository.

For any such device, ask the vendor: which fields, what units, sampling cadence, whether the summary
is model-generated, retention, on-device processing, export format, regional availability and written
commercial rights to store, analyse and redistribute derived data.

## Checklist before writing a single line of connector code

1. Exact device model, firmware and app/API version.
2. Permission route, whether it is user-authorized or contract-authorized, and its renewal cost.
3. Measured versus vendor-derived versus user-entered fields, labelled separately.
4. Original units, sampling window, local-versus-UTC time, and interval versus daily total.
5. Missing data, wear detection, quality flags and duplicate records.
6. Rate limits, backfill, deletion and revocation behaviour.
7. Written commercial rights to store, analyse and redistribute derived data.
8. A sample export run end-to-end through the adapter **before** any product commitment.

## Standing warning

Access can vanish. Aggregator libraries, community bridges and unofficial routes may stop working
after a firmware update, a policy change or a regional rollout, and their existence never implies
vendor permission. Re-verify this playbook at procurement time, not at design time.
