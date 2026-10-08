# v0.5 产品路径

当前需求、授权、结构化行动与投递边界见 [插件接口](plugins.md) 和 [输出契约](structured-advice.md)。下面保留旧分析/monitor 研究架构。新入口为 intent → user confirmation → permissions → care → outbox → feedback。

# Architecture: from device choice to a controlled daily notice

## User journey and implementation boundary

| Step | Current implementation | Required for a consumer deployment |
| --- | --- | --- |
| Choose | `healthos models --query ...` lists 20 representative model/platform rows; `healthos plan` checks selected-model fields against user goals; `healthos devices --goal ...` ranks working offline data paths | Exact model/region compatibility, terms, cost and independent usability testing |
| Acquire | A user supplies a permitted local export; adapter plugins parse it | Vendor OAuth/SDK grants, renewal, paging, offline gaps and revocation |
| Normalize | Strict metric/unit/timezone model with source and device provenance | Versioned schema, signal quality and duplicate handling across data stores |
| Calibrate | 28-day candidate baseline, minimum 14 valid days; device/source isolated | Prospective measurement and subgroup calibration studies |
| Detect | Three recent dates, median/MAD and explicit metric-specific research rule | Analytical/clinical validation, false alert measurement and clinical review |
| Decide to surface | Goal filter, 7-day per-stream cooldown and weekly budget | User controls, quiet hours, sensitivity preferences and acceptability study |
| Explain | Local template by default; optional LLM rewrites selected aggregates | Safety evaluation, privacy/DPA review, localization and human review |
| Deliver | Local JSON output with persisted state | Authenticated app delivery, consent, audit, deletion and incident response |

The [user journey](user-journey.md) connects the model catalog, local questionnaire, monitor and bounded suggestions. The rule is deliberately separate from the LLM. An LLM failure cannot make a new metric cross the rule or alter calibration. Outputs remain inspectable even when narration is disabled.

## Contracts

`Observation` in `model.py` is the canonical input. It has pseudonymous `user_id`, timestamp with offset, exact metric/unit, numeric value, `source`, `device_id`, a quality value and context. A source plugin implements `read(path, user_id)` and yields these objects. The included JSONL reader rejects a mismatched configured user ID.

`analysis.analyze(observations, as_of)` returns a versioned report. It never pools different `source` or `device_id` streams. `quality` is an input-integrity flag, not proof of sensor accuracy. A missing day is missing, never zero. Same-day aggregation assumes source records describe the same measure; interval steps and sleep segments need separate adapters.

A notice policy implements `select(report, state, as_of, settings) -> list[dict]`. The built-in policy accepts only `notable_change` rows, applies a per-stream cooldown and weekly notice cap, and writes its bookkeeping into state. A custom policy can be loaded as `your_module:Class`, but must preserve clinical and notification safeguards for production.

A narrator implements `render(notice, settings) -> str`. `none` uses a local template. `openai_compatible` calls a user-configured HTTPS Chat Completions endpoint. A custom narrator can be loaded as `your_module:Class`; plugin code has the caller's local privileges and should be audited. Neither built-in nor custom narrator changes `report` or decides whether a notice exists.

The CLI writes a JSON envelope: `report`, `notices`, `goals`, `delivery`, `clinical_status`. The caller's scheduling/delivery system owns timing, retries, UI and notification permissions. The same state file must be reused to suppress duplicate notices. To avoid concurrent writes, run one monitor process per state file at a time.

## LLM boundary

Default operation is offline. A cloud call requires both provider configuration and `--allow-cloud-health-data` on that invocation. The built-in HTTP client reads the API key from an environment variable, requires HTTPS and never writes the key to disk or output. It sends only one notice's metric, unit, aggregate values, valid-day counts and rule version. It does not send raw records, pseudonym, device ID, dates or context. However, those aggregates are still health-related data. Review the chosen provider's data retention, region and terms before using real records. The prompt asks for plain wording and no diagnosis, but prompt text is not a safety guarantee; users should inspect generated text.

For an OpenAI-compatible endpoint, a configuration shape is:

```json
"llm": {
  "provider": "openai_compatible",
  "endpoint": "https://api.example.com/v1/chat/completions",
  "model": "your-compatible-model",
  "api_key_env": "HEALTHOS_LLM_API_KEY"
}
```

This repository does not obtain an API key, assume a particular vendor is compatible, or test live calls. [OpenAI's API documentation](https://platform.openai.com/docs/api-reference/chat/create) describes the Chat Completions shape; compatibility and retention vary by provider.

## Failure and misuse cases to test next

Reused `sourceName` across two Apple devices can cause an accidental shared baseline. A production adapter needs a stable hardware identity or must detect ambiguous provenance. Travel and shift work can shift local dates. Vendor summaries can be revised after ingestion. The current state file is single-writer only. The policy intentionally provides no urgent escalation; treating it as an emergency monitor would be unsafe. See [validation](validation.md) and [clinical review](clinical-review.md).


## v0.4 开发版补充

新增自愿授权、多来源动态计划、行动建议、SQLite 投递与反馈及可选飞书文本发送。旧 monitor 仍是研究兼容路径，其生成候选即更新冷却的逻辑不适用于新闭环。实验性 Google Health 读取器仅处理已保存的 Fitbit 静息心率；没有新增实时同步。实际能力与限制见[个性化闭环](personalized-care.md)。
