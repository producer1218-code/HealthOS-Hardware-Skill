# Method v0.1: a transparent personal baseline

**Purpose:** detect a candidate change in an individual's own longitudinal data after a quiet calibration period. This is a software research rule. It is not a clinical risk score, a psychological diagnosis, or an emergency monitor.

## Pipeline

```text
local file → adapter → canonical observation → validation → daily value
           → per-user + per-source + per-device + per-metric baseline
           → candidate change and full explanation → JSON report
           → goal filter → cooldown / weekly notice budget → local JSON notice
           → optional LLM wording, only after explicit cloud opt-in
```

1. Accept only known metric/unit pairs, finite values and timestamps with timezone offsets. Reject input integrity quality below `0.8` and observations outside the 31-day analysis span.
2. Aggregate duplicate records on a local date with a median, except `steps_count`, which uses the maximum of cumulative daily totals. Raw step intervals are not accepted by the Apple adapter.
3. Reserve the **last three local dates** as the recent window. The preceding **28 dates** are available for baseline. Require at least 14 valid baseline dates and all three recent dates. Missing days are not zeros.
4. Baseline `B = median(baseline daily values)`; recent `R = median(recent daily values)`. Median absolute deviation `MAD = median(|xi − B|)`. `scale = max(1.4826 × MAD, metric-specific floor)`.
5. For a metric's predeclared concerning direction, calculate `directed_change = R − B` for higher or `B − R` for lower. Mark `notable_change` only when `directed_change ≥ minimum absolute change` **and** `directed_change / scale ≥ 2.5`.
6. If the metric has no proactive rule, output `trend_only`. The report returns all windows, counts, baseline, recent value, delta, scale and reason.
7. The separate `monitor` layer retains only the user's configured goals and creates a local notice for `notable_change` rows. The default policy uses a seven-day per-stream cooldown and at most two notices in a rolling seven-day window. It writes local state for duplicate suppression. These budget values are also engineering assumptions, not evidence-based intervention doses. No push transport is included.
8. Optional LLM narration is downstream of the rule and policy. It may reword a notice but cannot add one or override a status. Its output is not clinically reviewed.

| Prototype rule | Direction | Minimum change | Scale floor |
| --- | --- | ---: | ---: |
| Resting heart rate | Higher | 5 bpm | 2.5 bpm |
| HRV RMSSD | Lower | 8 ms | 5 ms |
| HRV SDNN | Lower | 8 ms | 5 ms |
| Sleep duration | Lower | 45 min | 25 min |
| Self-reported energy | Lower | 2 points | 1 point |

**Every value in this rule table is an engineering assumption chosen to make the prototype testable. None is a validated clinical threshold.** The 14-day minimum and 28/3-day windows likewise require prospective testing. A stable but unhealthy baseline can hide risk; a baseline comparison must never be described as a health clearance.

## Why these restrictions exist

- HRV interpretation depends on collection conditions, device, extraction and analytic choices. RMSSD and SDNN remain separate; exercise, sleep state and breathing can confound comparison. See [Laborde et al., 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/) and [Quintana et al., 2016 reporting guidance](https://pmc.ncbi.nlm.nih.gov/articles/PMC5070064/).
- Wearable sleep estimates do not replace polysomnography, especially for detailed sleep stage claims. See this [2025 meta-analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC11874098/). Accordingly, this prototype only compares total sleep duration supplied by an adapter.
- Digital biomarker development requires technical verification, analytical validation and clinical validation. See [Daniore et al., 2024](https://www.nature.com/articles/s41746-024-01151-3). A correct unit test proves software behavior, not clinical utility.
- Behavior suggestions should ask about capability, opportunity and motivation before interpreting nonadherence, following the [COM-B behavior change framework](https://pubmed.ncbi.nlm.nih.gov/21513547/). This intervention layer is a roadmap item, not implemented here.

## Known limitations

Local calendar dates can vary with travel and shift work; the current implementation does not detect either. `quality` is an input integrity indicator and not an independent sensor accuracy score. Vendor summaries may have different measurement windows; device isolation alone does not make them comparable. A low HRV or short sleep episode may have many explanations. Alerts, personalized recommendations and risk predictions should only be added after user research and validation.
