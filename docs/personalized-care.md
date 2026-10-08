# 自愿数据 → 动态计划 → 有依据的行动 → 反馈

v0.5 开发版通过本地网页 `healthos serve` 或终端 `healthos start` 引导目标、数据入口和授权，再定期检查与推送。完整普通用户路径见 [快速开始](../README.zh-CN.md)。原生手机界面、语音、飞书卡片回调、专家审核平台和健康改善效果验证尚未实现。

## 用户路径

1. 选目标和优先级：睡眠、恢复、活动、身体指标、自述精力等。自由文本保存在本地，目前不会由 LLM 自动生成监控规则。
2. 选已有入口：解释导出步骤和本代码真正可读的字段；没有文件也可以先看计划。
3. 自愿选指标，分别授权本地分析、主动提醒、外部平台接收摘要；默认都关闭，可以拒绝、到期或撤回。
4. 根据实际数据显示监控中、校准中、数据不完整、等待数据或可选接入/自述。缺失不填零，来源不混算基线。
5. 持续变化满足研究规则时提供个人趋势行动；明确选择的目标也可在有近期记录时收到一般目标行动，清楚标注不是异常发现。两者都有观察、依据、行动和反馈，目标顺序不代表医学严重度。
6. 分别记录行动执行和后续感受；不适合我或实施后感觉更差会暂停同类行动（不认定因果）。点击不是执行，执行不是健康改善，前后变化不是因果证据。

## 运行

Python 3.10+，推荐 3.12；macOS 系统 python3 可能仍是 3.9。

```bash
export PYTHONPATH=src
python3.12 -m healthos care-demo --output-dir care-output/demo
python3.12 -m healthos onboard --output data/private/care_profile.json
python3.12 -m healthos connection-plan --profile data/private/care_profile.json --output care-output/connection-plan.json
python3.12 -m healthos care --profile data/private/care_profile.json --state data/private/care.sqlite3 --output care-output/latest.json
python3.12 -m healthos dispatch --profile data/private/care_profile.json --state data/private/care.sqlite3 --output-dir care-output/delivered
```

care-demo 仅生成合成数据，跑通授权档案、动态计划、候选、本地投递和合成执行反馈，重复运行不会重复发送。care 默认使用用户时区的昨天，拒绝未完成的今天。历史回放生成的候选若已过期就不会派发。

示例档案见 examples/care_profile.json，授权默认为空。合成演示中的授权不能当作真实用户同意。

```bash
python3.12 -m healthos feedback --profile data/private/care_profile.json --state data/private/care.sqlite3 --notice NOTICE_ID --status executed
python3.12 -m healthos feedback --profile data/private/care_profile.json --state data/private/care.sqlite3 --notice NOTICE_ID --status unchanged
```

executed / skipped / not_relevant 是执行层；felt_better / unchanged / felt_worse 是独立自述结果。当前不自动学习疾病阈值或宣称干预有效，本地网页可记录反馈；目前没有反馈编辑 UI。用户可删除本地反馈或通过 preferences.disabled_actions 禁用行动。

## 可插拔边界

| 边界 | 首版实现 | 扩展接口 |
| --- | --- | --- |
| 数据 | Fitbit 官方导出 ZIP/目录、JSONL/CSV、Apple 部分数量记录、WHOOP 保存响应、旧 Google Health RHR 响应 | module:Class.read(path, user_id)；声明 metrics 和 setup_steps |
| 授权 | 来源、指标、用途、授权时间、到期与撤回 | 生产服务另补用户认证、授权审计和厂商 OAuth 同步 |
| 规划 | 授权、目标顺序、实际数据、缺测和反馈每轮重算 | 可替换本地/AI 需求理解，目标需用户确认；语音尚未实现 |
| 建议 | 版本化一般健康行动、原始来源和支持范围 | module:Class.propose(result, profile, feedback) |
| 投递 | 本地 JSON；可选飞书机器人文本 | external: bool 和 send(notice, settings) 返回确认 ID |
| 闭环 | SQLite 保存候选、投递、执行和自述结果 | 已认证手机/飞书回调调用 record_feedback |

插件是可信 Python 代码，接口不是沙箱。通用本地读取器可能解析整个用户所选导出，但只让授权且目标相关的字段进入分析。联网连接器必须另外在厂商 OAuth 和请求范围限制数据，不能靠事后过滤宣称最小采集。

Google Health 适配器仅解析本地 points[].dailyRestingHeartRate 中 Fitbit 来源，按 calculationMethod 拆分序列，不猜 Apple 的方法。日期使用上海时区中午作日记录锚点，不假装测量时间；displayName 是临时设备标识，多个同名设备必须在正式适配器中解决歧义。依据：[官方 REST 数据点结构](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints)。

## 基于专家内容，而不虚构专家审核

内容与触发规则分开。内置行动有来源、版本、范围和 review_status，明确标记 primary_source_based_not_clinician_reviewed。

[CDC 的睡眠习惯和日记建议](https://www.cdc.gov/sleep/about/index.html)支持规律作息、睡前减少电子设备和记录背景；[HRV 测量建议](https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/)支持核对方法与情境。它们不验证本模块的 28/3 天窗口、MAD 或精确变化门槛。

专业人员参与后需要实际的审查者、资质核验、日期、适用人群、排除条件、证据版本与复审时间。每条行动应说明为什么给此用户、证据支持什么、如何判断执行与复盘。当前只接受声明为 general_wellness 的插件输出；格式正确不等于医学正确，自定义内容须人工审核。

首版主要覆盖睡眠变化后的可行习惯/轮班日记，以及恢复或精力变化后的记录条件核查。活动步数可用于明确请求的一般活动规划，不作为已达到运动强度的证明。长期不理想但稳定的基线不会触发变化规则；目标行动是独立路径，不能把没触发当健康达标。

## 飞书设置

依据：[发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)、[自建应用 token](https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal)。

先创建应用机器人、开通消息权限并发布，用户需在应用可用范围。代码不自动申请权限或查找收件人。密钥使用环境变量 HEALTHOS_FEISHU_APP_ID 和 HEALTHOS_FEISHU_APP_SECRET，不写入档案。

```json
{
  "plugin": "healthos.feishu:FeishuDelivery",
  "recipient_user_id": "your-local-user-id",
  "receive_id_type": "open_id",
  "receive_id": "your-own-feishu-open-id"
}
```

将 `examples/feishu_delivery.json` 复制到 `data/private/feishu_delivery.json`，替换本人接收 ID。本地网页默认代号 local-person，需要与 recipient_user_id 一致。设置环境变量 HEALTHOS_FEISHU_APP_ID / HEALTHOS_FEISHU_APP_SECRET 后，用 `healthos serve --delivery-settings data/private/feishu_delivery.json --allow-external-delivery` 启动，在页面勾选外发授权。iPhone 飞书的系统通知开关由用户开启。

recipient_user_id 必须匹配档案。仅支持具体用户 open_id/user_id，不支持群发。用户还需针对指标授权 external_delivery，并在本次命令显式带 --allow-external-delivery。

```bash
python3.12 -m healthos dispatch --profile data/private/care_profile.json --state data/private/care.sqlite3 --settings data/private/feishu_delivery.json --allow-external-delivery
```

发送摘要含指标、日期以及适用时的基线和近期值，目标行动没有伪造基线；仍是健康数据；不含原始记录、设备、录音或生活细节。当前飞书是文本发送；反馈在电脑本地网页完成，手机消息没有可用的反馈按钮。卡片/事件回调还需身份验证、用户绑定和幂等后调用 record_feedback。

## 投递、撤回和数据保留

pending → sent / failed / uncertain / cancelled / expired。候选不花预算；明确失败可下一轮重试；成功才记冷却。每次派发重查授权、目标、拒绝、时段和预算。

消息请求后的网络中断可能已被服务端接受：飞书插件记 uncertain，暂占预算并停止自动重试，等待人工对账。远端幂等键有服务商范围/期限，不承诺永久 exactly-once。SQLite 事务串行派发，适合个人/小规模；无自动对账、退避调度或高吞吐队列。

撤回会在下次派发取消未发送候选并清除载荷，不删除原始导出、已送文件或飞书副本。forget 命令只删除对应用户的本地队列与反馈。数据库无应用层加密；报告和档案应放私有目录，生产部署另补权限、保留与删除机制。

旧 monitor 保留研究兼容性，仍在候选生成时更新旧 JSON 状态。新产品应使用 care → dispatch。

## 验证范围

合成测试覆盖授权、来源、时区、错用户、过期、插件错误、失败/模糊投递、预算、去重、反馈与完整 CLI。飞书仅模拟 HTTP，没有真实账号发送。测试通过不等于临床有效或证明使用户更健康。
