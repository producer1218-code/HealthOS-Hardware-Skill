# Roadmap: from open research core to consumer system

## Phase 0 — included in this repository

Published-source 20-row model/platform catalog, evidence map, local goal questionnaire and measurement plan, canonical data schema, four working offline adapters, deterministic baseline prototype, goal-based device-path helper, stateful one-pass monitor, bounded next-step suggestions, conservative notice policy, optional BYO-LLM narration, tests and reproducible synthetic demo. It can be scheduled externally but is not a deployed always-on service.

## Phase 1 — interoperability research

Obtain permitted sample exports or sandbox access for Apple, Xiaomi, Huawei, Zepp and Google as available. Record exact device and API versions. Add interval-aware sleep/activity aggregation, data-quality provenance and adapter contract tests. For raw-signal research, evaluate Polar or a contracted ODM separately.

## Phase 2 — measurement validation

Partner with relevant clinicians, sleep researchers and behavioral scientists. Validate each target metric and prespecify failure cases. Study calibration length and personal-change rule behavior. Publish negative results and subgroup performance as well as successful findings.

## Phase 3 — consumer experience

Implement quiet calibration, user-controlled check-ins, explainable weekly reports, contextual questions and a notification budget. Allow users to mute, correct and delete data. Keep a transparent separation between observation, hypothesis and action.

## Phase 4 — product and open community

Build consented accounts and security controls, field-test paid value, document API compatibility, write public reproducibility notes and invite contributions. Publish only evidence-backed health claims. Maintain a public changelog and model cards so third parties can audit changes.

Suggested first issue labels: `device-evidence`, `adapter`, `measurement`, `validation`, `docs`, `good-first-issue`.


## v0.4 开发版补充

新增自愿授权、多来源动态计划、行动建议、SQLite 投递与反馈及可选飞书文本发送。旧 monitor 仍是研究兼容路径，其生成候选即更新冷却的逻辑不适用于新闭环。实验性 Google Health 读取器仅处理已保存的 Fitbit 静息心率；没有新增实时同步。实际能力与限制见[个性化闭环](personalized-care.md)。
