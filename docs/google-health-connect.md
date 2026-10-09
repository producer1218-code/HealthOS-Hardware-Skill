# Fitbit Air：把手环数据交给自己的 HealthOS Agent

核验日期：2026-10-09。先在手机上正常同步 Fitbit Air 到 Google Health。拥有手环不等于拥有开发者 API 项目权限。

## 1. 判断你能走哪条路

[Google Health 官方入口](https://developers.google.com/health)目前说明暂停新项目接入，旧 Fitbit Web API 在 2026-10-30 关闭。新用户先申请或关注官方开放状态；已有获准项目可继续。创建 Cloud 项目、OAuth 客户端或添加测试用户并不自动获得资格。

没有资格：按[官方导出说明](https://support.google.com/googlehealth/answer/14236615)下载归档；本地页面选 Fitbit 导出并逐项授权。你仍可获得同样结构的报告，更新依赖新的导出。申请被拒不会阻止你使用合法导出。

## 2. 准备自己的项目

按[Google Cloud/OAuth 设置](https://developers.google.com/health/setup)启用 API，配置同意屏幕、测试用户和只读范围。在 Google Health 手机应用用目标 Google 账号登录并完成关联。

HealthOS 使用 Google 官方 google-auth-oauthlib 和 google-auth 库，在系统浏览器授权。可使用 Cloud 下载的 Web 客户端 JSON，登记精确回调地址 `http://127.0.0.1:8766/`。Desktop 客户端是否可用须以获准项目规则为准。OAuth Playground 的回调地址不适用于此连接器。

| HealthOS 字段 | Google 数据类型 | 只读范围 |
| --- | --- | --- |
| 静息心率 | daily-resting-heart-rate | googlehealth.health_metrics_and_measurements.readonly |
| 日均 RMSSD | daily-heart-rate-variability | 同上 |
| 已处理主睡眠时长 | sleep | googlehealth.sleep.readonly |

范围带 `https://www.googleapis.com/auth/` 前缀。Google 健康指标范围包含多个字段；HealthOS 再按你选择的字段限制请求和分析。此版本未实现 API 步数、血氧或皮温，不能用设备兼容列表代替实际代码能力。

## 3. 加密存储，启动浏览器授权

[Google 数据政策](https://developers.google.com/health/policies/health-api-developer-user-data-policy)要求健康记录、派生数据和凭证在静态存储时加密。把客户端 JSON、整个私人工作目录、导出、报告和 SQLite 文件放在启用 BitLocker、FileVault 或等效加密的存储上。HealthOS 依赖系统加密，不检测磁盘、不提供应用层加密。确认实际配置后才使用下方确认参数；文件权限不等于加密。

```bash
python -m pip install -e ".[google]"
healthos connect-google --client data/private/personal/client.secrets.json --connection data/private/personal/google --metric sleep_minutes --metric resting_heart_rate_bpm --metric hrv_rmssd_ms --encrypted-storage-confirmed
```

在浏览器检查应用、账号和只读范围后同意。连接器先调用 users/me/identity 验证关联，再保存本机凭证。不要把授权码、客户端密钥或 oauth.json 发给 LLM、GitHub 或作者。

403 / 项目不可用：核对资格和 API 状态，使用导出回退。账号未关联：先完成手机应用关联。没有 refresh token：重新同意离线访问。回调不匹配：登记上述回调。失败请求不会被解释为健康正常，也不会用旧快照伪造新数据。

## 4. 在 HealthOS 确认指标和用途

运行 healthos serve，填写目标，选择 Google Health API，在目录栏填写 connection 目录的绝对路径。选择指标，分别授权本地分析、主动通知、需要的外部推送。

OAuth 和本地用途授权是独立检查。撤回本地分析后，不再初始化连接器或请求这些指标；还需在 Google 账号的第三方连接管理中撤销应用、删除本地 connection 目录，才能移除厂商凭证。

每轮读取最近 45 个已完成日期；睡眠按结束时间过滤并归入醒来日，日指标按用户时区民用日期锚定。只读取明确标为已处理且主睡眠的时长；不使用阶段推断疾病。HRV 日均与深睡 RMSSD 不混用，不同 RHR 计算方法也不混用。[Google 字段](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints)和[过滤说明](https://developers.google.com/health/filters)是映射依据。

只接受 Fitbit 来源，未知设备元数据跳过。设备摘要不是硬件 ID；两台同名设备可能无法分开，需人工核对。连接器有模拟分页和过滤测试，真实账号兼容性仍需验证。

## 5. 模型、报告和记忆

按[中文首页](../README.zh-CN.md)配置自己的模型并开启报告。模型与飞书分享分别授权。Google 用途限制也适用于聚合数据；传递到第三方须用于明确授权的报告功能并符合分享条件，聚合不是自动豁免。

记录执行、适用性和自述感受；反馈用于调整行动，不证明效果、不自动创建医学阈值。查看 memory.json、清除记忆或撤回授权。

可以把这句话交给另一位 Agent：

> 请先读 HealthOS 的 docs/agent-handoff.md，指导我检查数据接入资格和字段。我确认目标与权限后，用本机 agent-packet.json 按仓库方法解释报告，保留缺失、来源和证据边界。不要读取或索取 OAuth 凭证，不要把设备估计说成诊断。
