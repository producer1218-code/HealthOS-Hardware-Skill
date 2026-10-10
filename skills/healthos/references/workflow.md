# Existing wearable to personal agent

Reviewed 2026-10-09; implementation v0.6 development. Public repository: https://github.com/producer1218-code/HealthOS-Hardware-Skill . Consult the repository's current field table and vendor access rules when connecting real accounts.

## Choose a permitted source

| Reader | Parsed subset | Operational condition |
| --- | --- | --- |
| fitbit-takeout | sleep_minutes, resting_heart_rate_bpm, explicit hrv_rmssd_ms, steps_count | Official ZIP/folder subset. Refresh export manually; not all versions verified. |
| google-health-api / google-health-json | resting_heart_rate_bpm, daily-average hrv_rmssd_ms, processed main-sleep sleep_minutes | Fitbit-origin records only; eligible projects for API, not new-project eligibility. Encrypted-storage attestation required for live access. No live steps, SpO2 or temperature. |
| apple-health-xml | heart_rate_bpm, resting_heart_rate_bpm, hrv_sdnn_ms, spo2_pct, skin_temp_c | User export; no sleep_minutes or steps_count parsing. SDNN is not RMSSD. |
| whoop-v2-json | resting_heart_rate_bpm, hrv_rmssd_ms, spo2_pct, skin_temp_c, sleep_minutes, respiratory_rate_bpm | Already authorized saved API responses; no online WHOOP OAuth. |
| csv / jsonl / Python plugin | Canonical fields actually mapped by operator | Mapping is not proof of device support or accuracy. |

Huawei, Xiaomi, Amazfit, OPPO and vivo have research catalog entries but no dedicated adapters here. Do not guide a user as though these brands are already integrated.

Google official access status: https://developers.google.com/health . An OAuth client does not grant API eligibility. No eligible project? Use the user's official export route: https://support.google.com/googlehealth/answer/14236615 . Live Fitbit Air account/device results remain unverified.

## Establish a user plan

Use the user's confirmed goals, relevant volunteered context and selected metrics. Keep permissions distinct: vendor access, local analysis, notification, external transport and model sharing. For each unsupported goal, identify the missing field or context instead of promising a result. The repository's deployment guide handles commands and configuration; don't request credentials to interpret a report.

## Interpret an agent-context-v1 packet

Expected fields: schema_version, as_of, goals, memory, coverage, period_summary, personal_trends, goal_states, actions, methodology and agent_contract. Format alone does not prove consent or authenticity. The packet reflects a snapshot; confirm current processing permission rather than relying on historical consent.

- period_summary compares the latest seven completed dates to the previous seven; fewer than three valid dates in either window is insufficient_coverage. Missing days are not zero.
- Personal trend hypotheses compare a 28-day candidate baseline (at least 14 valid baseline days) with three recent valid days using median/MAD and metric-specific gates. Preserve the actual status; lack of a trigger is not evidence of health.
- Keep separate source, device and calculation method streams. New device/method data need a separate baseline. Provisional Google device metadata cannot always separate identical devices.
- RMSSD/SDNN and daily versus deep-sleep RMSSD must remain distinct. Device estimates do not establish diagnoses or psychological traits.

## Form a reviewable report

Preserve deterministic facts and evidence. Explain what the user can check, propose feasible guideline actions already present in the report, and ask about capability/opportunity/motivation when relevant. Feedback records execution separately from self-reported outcome; negative suitability feedback pauses an action.

Evidence supports measurement discipline and general-wellness discussion: HRV measurement recommendations https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/ ; COM-B https://pubmed.ncbi.nlm.nih.gov/21513547/ ; CDC sleep https://www.cdc.gov/sleep/about/index.html . These sources do not validate the runtime, its alert thresholds or intervention efficacy.

The report-aggregate-v1 external-model packet excludes identifiers, dates, raw observations and free-text context in the bundled renderer. Full local packets are sensitive. Retain the configured recipient and consent checks. Default reporting works without a model; invalid model output falls back to deterministic prose.

## Recurrence and limits

The runtime supports 7/14/30-day UI cadence while the summary window stays seven completed days. A configured process must remain running; the skill and GitHub do not execute private jobs. Delivery needs its own authorization and channel. No MCP server, clinician sign-off, validated clinical effects or universal host compatibility is supplied by this skill.
