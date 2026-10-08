# 结构化输出：care-v2

`latest.json` 是 UI / 推送消费者的统一输出，保存在私有 workspace。不要把真实结果作为 GitHub issue 附件。

| 字段 | 意义 |
| --- | --- |
| version / user_id / as_of | 契约版本、本地代号、已完成分析日 |
| plan.runtime_goals | 目标、monitoring / calibrating / data_incomplete / waiting_for_data / optional_connection_or_self_report |
| plan.replan_reasons | 授权检查时间、反馈数量和暂停行动原因 |
| source_status | 入口状态、实际指标、导入诊断；失败有安全错误类型 |
| streams | 来源/设备/指标、最新日期、有效日数、过旧天数 |
| report | 版本化个人趋势分析、样本数与窗口 |
| recommendations / candidates | 同一组可展示建议；候选不是成功推送 |
| delivery_result | sent / failed / uncertain / cancelled / expired / deferred 本轮计数 |
| data_status | available / waiting_for_data / source_error |
| next_questions | 目标仍缺的自愿背景问题 |

下面是简化的合成建议示意；完整运行输出还包括权限、来源覆盖和投递状态。

```json
{
  "goal": "sleep",
  "trigger": {
    "kind": "user_requested_goal_coaching",
    "validation": "general_wellness_not_anomaly"
  },
  "observation": {
    "metric": "sleep_minutes",
    "latest_record_date": "2026-10-07",
    "valid_record_days": 1,
    "rule_version": "goal-coaching-v1"
  },
  "why_you": "这是你确认的目标行动，已有相关记录；并非发现疾病或异常。",
  "advice": {
    "action_id": "sleep-routine-v1",
    "action": "今晚选一个可行的睡前收尾时间，睡前半小时放下电子设备；明早记录感受。",
    "question": "这个动作适合你今晚的安排吗？",
    "evidence": [{
      "title": "CDC About Sleep",
      "url": "https://www.cdc.gov/sleep/about/index.html",
      "supports": "一般睡眠习惯；不支持此系统的触发阈值。"
    }],
    "scope": "general_wellness",
    "content_version": "guideline-advice-v1",
    "review_status": "primary_source_based_not_clinician_reviewed",
    "success_check": "实际执行、可行性与次日自述；不推断因果。"
  },
  "feedback_options": ["executed", "skipped", "not_relevant"],
  "outcome_options": ["felt_better", "unchanged", "felt_worse"],
  "delivery_status": "sent"
}
```

个人趋势触发 kind=personal_trend，observation 会包含 baseline_median / recent_median / baseline_n_days / recent_n_days / windows / rule_version。目标行动不能伪造这些值。两者都保留稳定 ID、source_id、stream_key、有效期。

每次生成和送达分开：pending 建议可展示但不接受“已送达反馈”，UI 显示状态；local-json 成功写入视为本地送达，不证明用户阅读。外部发送不包含原始测量、设备、录音或问答原文。摘要仍是健康数据，需外发授权。
