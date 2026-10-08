# Research process and evidence limits

Snapshot date: 2026-10-08. This is a **targeted desk review**, not a PRISMA systematic review or a clinical guideline. The objective was to decide which wearable data can be obtained for an open algorithm prototype and what validation is required before consumer claims.

## Questions

1. What signal hardware and user-facing metrics are publicly listed for representative products?
2. Which documented paths allow a user-authorized third party to access data?
3. Is the accessible data raw waveform, intervals, samples, daily summaries or vendor scores?
4. Which published methods help define measurement quality, behavior feedback and validation?

## Source selection

Device features come from current manufacturer specifications or support pages. Developer access comes from official developer/API documentation when available. Scientific interpretation comes from publisher or indexed primary papers, reviews and WHO/FDA documents. Third-party open implementations are cited only to illustrate community interoperability, not as manufacturer permissions. A public claim was marked **unconfirmed** when no relevant official interface could be verified.

Search terms included combinations of product/model + sensor/specifications, developer API, HealthKit/Health Kit, PPG waveform, HRV, polysomnography, digital biomarker validation, COM-B and WHO-5. The set is selective; it does not represent all devices or all studies. Source URLs and judgments are preserved in [device-matrix.md](device-matrix.md) and [literature.md](literature.md).

## Evidence hierarchy used here

1. Original technical documentation for a **documented capability**.
2. Independent measurement study or systematic review for an **accuracy or interpretation claim**.
3. Manufacturer feature page for **marketed availability**, never as independent proof of accuracy.
4. Project engineering choice for the **prototype rule**; explicitly not attributed to literature.

## Gaps to resolve with collaborators

No clinician has reviewed the signal rules; no consumer user study has tested comprehension; no hardware model has been benchmarked by this project; no vendor API approval has been obtained; no real health record is included. The device matrix must be refreshed at the moment of procurement or integration, as access and regional feature availability can change.
