# Personal health observation method

This protocol is usable by a URL-reading agent before software installation. It is a conversation and planning method, not a new implemented analysis engine. Ask only what is missing from the current conversation. A device name and an LLM key do not establish data access or permission.

## 1. Discover the user's question and device

Begin with: “你用什么型号的手环或健康设备，最想用它了解什么？” Explain that some devices expose data through user-authorized APIs, mobile health stores or official exports. Check the actual model, phone platform, desired fields, access eligibility and source documentation date. Distinguish vendor capability from the repository's implemented adapters using [workflow.md](workflow.md).

Do not make the user sit through a synthetic report before discussing their own goal. Offer the public example only if it helps them understand the proposed output. Discovering this repository is not permission to install it, collect records or start a recurring task.

## 2. Turn a concern into an answerable question

Let the user choose a question such as sleep regularity, daily activity or recovery around training. Ask about timing, recent changes and relevant context only as needed. Explain what the available fields can describe and what they cannot establish. Do not derive mood, disease or psychological traits from sensor data.

| User question | Candidate observations | Context to ask, when relevant | Interpretation boundary |
| --- | --- | --- | --- |
| Is my sleep schedule becoming more regular? | Sleep onset/wake times and duration, when accessible | Work shifts, travel, wear gaps, desired schedule | Duration alone cannot measure regularity; current runtime does not analyze onset/wake regularity |
| How do my recovery records vary around training? | Comparable resting HR and explicitly defined HRV; sleep duration | Training schedule, measurement conditions, perceived recovery | Associations are descriptive; a low HRV value does not establish illness or stress |
| Am I moving more consistently? | Daily steps or accessible activity duration | Work pattern, mobility constraints, what movement is feasible | Steps are not equivalent to moderate/vigorous exercise minutes; current runtime retains steps without a validated activity coaching engine |
| Why do I feel tired? | Optional self-reported energy, sleep and comparable recovery records | Onset, persistence, routines and symptoms volunteered by user | Wearables cannot determine the cause; do not delay appropriate care to collect a baseline |

## 3. Agree an observation plan

Return a short, reviewable plan in the user's language. Include:

- **Question and intended benefit:** the user's words, what a report should help them decide.
- **Device and access:** model, source, exact fields, units/method, official route, eligibility and implemented support status.
- **Permissions:** selected fields and purposes, processing location, retention/deletion preference; separate model sharing and delivery choices. Leave unspecified choices pending.
- **Observation:** collection cadence, available history, freshness/missingness checks and comparable stream separation. Use actual source latency, not an invented real-time promise.
- **Method and evidence:** link the applicable source and explain its support boundary. Label engineering choices separately. The bundled runtime's 28-day/3-day median/MAD logic is an unvalidated project hypothesis, not a clinical standard.
- **Report and review:** agreed report frequency, factual coverage, questions, feasible action and how execution/suitability/self-reported outcome will be reviewed.
- **Gaps and next step:** missing fields, context, connector or tools; say what can happen now and what needs setup.

Use [observation-plan-v1.json](observation-plan-v1.json) as an optional interchange template. It is an agent-authored proposal, not an executable profile, runtime consent object or API credential container. Unknown information remains null or pending. There is no automatic importer for this plan.

## 4. Interpret records with evidence

Before reading personal records, confirm the selected processing and recipient permissions. Check units, timestamps/timezone, latest data, duplicates, missing days, source/device and calculation method. Missing days are not zero. Keep RMSSD and SDNN separate, and keep daily and sleep-window estimates separate. A device/method change needs a new comparable stream.

Use the runtime's deterministic report facts if available. With only a planning conversation, do not fabricate baselines or claim monitoring has begun. A stable personal baseline does not establish health; sparse records require uncertainty rather than reassurance. For symptom or diagnostic questions, use appropriate clinical guidance rather than wearable pattern guessing.

Every report should distinguish **observed facts**, **possible explanations that need context**, **unknowns**, **evidence and its limits**, and **a feasible next step**. Guidelines support general-wellness discussion, not the clinical validity of this software.

## 5. Review actions and remember explicitly

Ask separately whether the action was attempted, whether it fit the user's life and what they experienced. Use capability/opportunity/motivation questions when selecting an action; no compliance score or psychological profile. One change at a time can make a review easier, but an uncontrolled before/after comparison does not prove causality.

Save only confirmed goals, volunteered context and authorized feedback in the user's chosen private store. Explain what was retained and how to correct/delete it. If no persistence tool exists, return an editable summary rather than claiming durable memory. Follow the user's selected report cadence and pause rules; do not invent an always-on scheduler.

## Evidence map

| Source | What it supports here | What it does not validate |
| --- | --- | --- |
| [Laborde et al., 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/) | HRV acquisition/context discipline and comparable measurements | Inferring stress or disease; HealthOS trigger thresholds |
| [COM-B, Michie et al., 2011](https://pubmed.ncbi.nlm.nih.gov/21513547/) | Capability, opportunity and motivation questions for feasible behavior | Automated psychological scores or proven intervention efficacy |
| [CDC sleep guidance](https://www.cdc.gov/sleep/about/index.html) | General sleep habits and diary discussion | Wearable sleep-stage accuracy or individualized diagnosis |
| [WHO activity guidance](https://www.who.int/publications/i/item/9789240014886) | General physical activity discussion | Equating steps with intensity or ignoring personal circumstances |

These existing sources underpin a proposed conversation protocol. It has not received clinician sign-off or prospective behavioral validation. Detailed calculations and implementation evidence are in the repository's docs/report-methodology.md and docs/evidence-to-code.md.
