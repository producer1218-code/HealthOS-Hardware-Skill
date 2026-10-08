# Validation plan before consumer claims

Software tests in `tests/` confirm parsing, units, missing-day handling, device separation and rule behavior on synthetic data. **They do not measure sensor accuracy or clinical performance.**

## Stage 1 — technical verification

Test each adapter on several export and firmware versions. Check timestamp offsets, duplicates, pagination, disconnections, resync, unit changes, revoked access and deletion. Record supported device/firmware versions. Obtain raw data only through a documented and permitted interface.

## Stage 2 — analytical validation

For each target metric define an appropriate reference: ECG or validated chest strap for heart timing, polysomnography for sleep measures, validated pulse oximetry for SpO₂ when relevant. Pre-register the comparison, report bias, error distributions, missingness and subgroup results. Include movement, skin tones, ages, sexes, fit/strap placement and device changes. Do not transfer validation from one model to another.

## Stage 3 — interpretation and user study

In an adult consumer cohort, test whether calibration length and change rules produce interpretable events. Measure false or unwanted notices, missed meaningful changes, comprehension, anxiety and user control. Record work schedule, travel, illness, alcohol, medication changes and self-reported context when users choose to share it. Review messages with clinicians and behavioral scientists.

## Stage 4 — intervention study

Define an outcome such as sleep regularity or self-reported energy, and compare actionable feedback with a suitable control experience. Track adherence and adverse effects. Avoid treating engagement or notification clicks as proof of improved health. Reassess claims and requirements separately for each sales jurisdiction.

Before any external pilot, prepare consent, ethics review where applicable, data retention/deletion, escalation for concerning self-reports, and the [clinical review worksheet](clinical-review.md). This plan does not itself authorize a study.
