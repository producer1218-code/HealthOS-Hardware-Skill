# From published science to one person's signal

Reviewed 2026-10-08. [method.md](method.md) specifies the arithmetic. This page explains the reasoning
that turns population-level health science into something about a single named person, and specifies
where the honesty boundary sits. Nothing here has been validated on people — it is a design argument
and an implementation plan.

## The translation problem

Published thresholds describe populations. A wearable shows one individual. Three failure modes follow,
and each one shapes the architecture:

1. **The population threshold is the wrong instrument.** A resting heart rate of 70 bpm is unremarkable
   in a guideline and possibly alarming for someone whose own stable value is 48. Comparing a person to
   a population loses the only comparison that carries information about them.
2. **A stable but poor baseline is invisible to change detection.** Someone who has slept badly for two
   years will never trigger a change rule. A baseline comparison is not a health clearance and must
   never be worded like one.
3. **Vendor scores hide their own assumptions.** Recovery, Readiness, Body Battery and stress indices
   are models fitted to a population, delivered without the coefficients. Using them as inputs means
   inheriting an unknown algorithm on top of a known one.

The project's answer is to move the reference point from the population to the person, keep the
calculation visible, and let science supply the *metric, direction and interpretation caveats* rather
than the *cutoff*.

## The chain, layer by layer

**Step 1 — establish a personal reference.** For each `user_id` + `source` + `device_id` + `metric`,
take the median over a 28-day baseline and the median over the last 3 days. Median rather than mean
because a single illness night or a stuck sensor should not define anyone's normal. Robust scale from
median absolute deviation, floored per metric, so a suspiciously flat week cannot manufacture a
trigger. Show the person their own baseline value and the window it came from — the number is
meaningless without its dates.

**Step 2 — demand a calibration period before saying anything.** Until 14 valid baseline dates exist,
the only correct output is `calibrating`. A new product that alerts in week one is describing the
population, not the user. A new device starts a new calibration; a device swap is a new instrument, and
treating two instruments as one series is the most common error in consumer health analytics.

**Step 3 — orient the metric by what is concerning, and say why.** Each metric gets a direction from
the literature, not from positive-means-good intuition: lower HRV is the concerning direction for
`hrv_rmssd_ms` and `hrv_sdnn_ms`; higher is concerning for `resting_heart_rate_bpm`; lower is
concerning for `sleep_minutes` and self-reported energy. Encode the direction as data, so a reviewer can
audit it rather than infer it.

**Step 4 — require two independent conditions.** A change must clear a metric-specific minimum
*and* reach a robust z of 2.5. Two conditions, because a tiny shift in a very stable person is
statistically loud and practically irrelevant, while a large shift in a noisy one is the reverse. Both
gates are visible in the report.

**Step 5 — name what a change is not.** `notable_change` means a research rule fired. It is not
illness, overtraining, depression, stress or recovery. This sentence must survive into every surface
that displays the result, including an API error message and a push notification.

## Which metrics can carry a claim, and which cannot

| Signal | Reasonable personal use | What must not be said |
| --- | --- | --- |
| Resting heart rate | Long-run personal drift; response to training load or illness | "Your heart is healthy" — it is one number, in one posture, at one time of day |
| HRV (RMSSD, SDNN) | Personal trend under stable collection conditions | "Your stress is high" — HRV is not a direct stress measure |
| Sleep duration | Total-time trend from the same device | Anything about sleep stages; consumer staging is not polysomnography |
| SpO₂ | Spot values, personal reference | Sleep-apnoea or respiratory diagnosis |
| Skin temperature | Personal deviation from own baseline | Fever, ovulation or infection |
| Respiratory rate | Personal deviation | Respiratory diagnosis |
| Steps | Adherence and personal trend | A health verdict from a count |
| Self-reported energy | Directly meaningful as subjective state | A physiological measurement |

RMSSD and SDNN stay separate because their calculation windows differ; merging them destroys the
comparison. Vendor composite scores stay outside this table entirely — a score whose definition is
undisclosed cannot be reviewed.

## Confounders the method does not yet handle

State these out loud rather than burying them: local calendar dates move with travel and shift work,
and the implementation detects neither; alcohol, illness, altitude, medication changes, caffeine and
menstrual phase all shift these metrics; cuff-based blood pressure is a separate instrument with its own
workflow and must not be pooled with optical estimates; wear time and fit change the signal as much as
physiology does. When a change fires, the honest product move is to ask, not to conclude — capability,
opportunity and motivation come before any assumption about nonadherence, following the COM-B framing
in [literature.md](literature.md).

## Delivery: how this reaches the person

Delivery is a product layer, planned but not built here. A proposed OS loop is: obtain a fresh,
user-authorized export → preserve source/device and metric semantics → pass quality/calibration gates →
produce a traceable per-device candidate → ask for optional context and delivery preference → show a
low-stakes message only after validation and user opt-in. A Looki-like lifelog may supply an optional
user-confirmed activity note, not a vital sign, diagnosis or inferred cause. Do not upload raw audio or
video as a prerequisite for the loop. Its constraints follow from the above:

- **One candidate per message, with its evidence.** "Your resting heart rate ran 5 bpm above your own
  28-day baseline over the last three days; you recorded these on 3 of 3 days." No composite
  wellness score, no colour-coded diagnosis.
- **A notification budget, and a mute.** A rule that can fire weekly forever will be muted within a
  month. Budget frequency, suppress during calibration, and let users mute by metric.
- **Comparison only within an instrument.** Never chart two devices on one line, and never compare
  a person's ring against a population of ring users.
- **A visible split between observation, hypothesis and action.** Observation: the numbers. Hypothesis:
  the candidate explanation. Action: an optional question or check-in. Collapsing these three is what
  turns a measurement tool into an authority it has not earned.
- **Questions over assertions.** Recording last night's alcohol, illness or travel converts an
  unexplained alert into a learnable pattern, and puts the user in control of interpretation.
- **Deletion and correction as first-class features.** A consumer health record the person cannot
  correct is a record they should not trust.
- **Context carriers inform, never conclude.** Notes from an AI recorder belong in `context`; they may
  prompt a question, never a physiological verdict.

## The first testable question

Not "can the algorithm detect illness." It is: **can a person understand and act on a device-specific
change in sleep duration, resting heart rate or self-reported energy without unnecessary anxiety?**
Feasibility outcomes are valid-data coverage and comprehension; report false and unwanted notices
alongside missed changes. Only after that does a reference-measurement study make sense, and only after
that an intervention study. The full sequence, including subgroup reporting and jurisdiction-specific
claim review, is in [validation.md](validation.md).

## Standing disclaimer

Every threshold on this page is an engineering assumption chosen to make a prototype testable. The
2025 sleep meta-analysis, the HRV reporting guidance and the digital-biomarker framework in
[literature.md](literature.md) support the *direction of work*, not these numbers.

## v0.4 开发版补充

新增自愿授权、多来源动态计划、行动建议、SQLite 投递与反馈及可选飞书文本发送。旧 monitor 仍是研究兼容路径，其生成候选即更新冷却的逻辑不适用于新闭环。实验性 Google Health 读取器仅处理已保存的 Fitbit 静息心率；没有新增实时同步。实际能力与限制见[个性化闭环](personalized-care.md)。
