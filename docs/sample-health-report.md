> 全部为合成数据，无真人、无真实设备采集、无模型或外部推送调用。以下数字仅演示报告结构。

# 你的定期健康观察报告

观察周期：2026-10-02 至 2026-10-08

依据公开指南与研究整理；尚未经过临床专家审核。

## 你的目标与数据可信度

- 睡眠：可以监控个人趋势
- 恢复与身体状态：可以监控个人趋势

| 指标 / 独立数据流 | 本周有效天数 | 本周中位数 | 上周中位数 / 天数 |
| --- | --- | --- | --- |
| 睡眠 HRV（RMSSD） / synthetic::synthetic-demo / demo-device | 7/7 | 42.0 ms | 43.0 ms / 7 |
| 静息心率 / synthetic::synthetic-demo / demo-device | 7/7 | 59.0 bpm | 58.0 bpm / 7 |
| 睡眠时长 / synthetic::synthetic-demo / demo-device | 7/7 | 445.0 min | 450.0 min / 7 |

## 相对你自己的变化

- 睡眠 HRV（RMSSD）（synthetic::synthetic-demo / demo-device）：未触发该研究规则；基线 28 天，最近 3 天。 最近中位数 32.0，基线 43.0 ms。
- 静息心率（synthetic::synthetic-demo / demo-device）：个人记录有变化，需要核对背景；基线 28 天，最近 3 天。 最近中位数 68.0，基线 58.0 bpm。
- 睡眠时长（synthetic::synthetic-demo / demo-device）：个人记录有变化，需要核对背景；基线 28 天，最近 3 天。 最近中位数 360.0，基线 450.0 min。

这些状态描述个人记录变化，不能判断病因；正常或没有触发也不能排除疾病。

## 下周可以尝试

- 今晚选一个可行的睡前收尾时间，睡前半小时放下电子设备；明早记录感受。
  复盘：记录是否实际执行、可行性与次日自述感受；不将一次变化归因为建议。
  依据：https://www.cdc.gov/sleep/about/index.html
- 先核对佩戴和记录条件，写下最近训练、旅行或作息是否改变；暂不判断原因。
  复盘：背景是否补齐，记录条件是否可信；不自动改变医学判断。
  依据：https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/

## 我目前了解的你

你确认的目标：睡眠、恢复与身体状态
你主动描述的背景（原样记录，不作诊断）：{"sleep": "合成背景：偶尔加班，希望行动足够小。"}
已记录反馈：{"executed": 1}
已暂停不适合或感觉更差的行动：暂无

## 下次需要确认

- 这周哪些工作、照护、旅行或佩戴条件改变了？
- 下周这个行动对你的能力、时间机会和意愿是否合适？

## 方法与证据边界

- [CDC sleep guidance](https://www.cdc.gov/sleep/about/index.html)：睡眠习惯和日记；不验证设备或趋势阈值。
- [HRV measurement recommendations](https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/)：解释 HRV 时需考虑测量条件；不能直接推断压力或疾病。
- [COM-B / Behaviour Change Wheel](https://pubmed.ncbi.nlm.nih.gov/21513547/)：行动前询问能力、机会和意愿；本项目实施效果尚未验证。

- 有效记录缺失时不填零；不同设备、来源和算法分别比较。
- 手环估计不是临床检查；无触发不表示健康达标。
- 基线规则尚未临床验证，执行和感受不构成因果证据。

![合成报告的本地页面](synthetic-report-ui.png)
