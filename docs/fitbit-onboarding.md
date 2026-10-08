# 用已有 Fitbit 开始

目标是让拥有 Fitbit 的普通用户通过自己下载的数据建立行动计划。无需 API 密钥或开发者申请。导出权限与可读取格式分别核对；不是任意 Fitbit 文件解析器。

## 取得数据

Google 账号：从 [Takeout](https://takeout.google.com) 选择 Google Health，申请导出、下载 ZIP。原 Fitbit 登录：账号设置 Data Export → Request Data，按邮件步骤取得归档。依据：[Google 官方导出说明](https://support.google.com/googlehealth/answer/14236615)。

在 `healthos serve` 页面选择 ZIP / 受支持文件，或展开本地目录输入解压目录。上传只是本地保存，分析之前仍需指标与用途授权。ZIP 超过 64MB 时改填解压目录；读取单个支持文件上限 32MB，总读取上限 512MB。ZIP 不解压，拒绝越界路径和异常压缩比。

## 实际读取契约

下表是针对观察到的官方导出子集建立的格式契约，不保证所有账号/地区/设备都有这些文件；导出格式可能变化。测试数据全部自行合成，没有公开真实导出。厂商 API 的[睡眠字段定义](https://dev.fitbit.com/build/reference/web-api/sleep/)帮助解释字段，不能当成所有 ZIP 格式承诺。

| 文件 | 实际使用字段 | 处理 |
| --- | --- | --- |
| `daily_resting_heart_rate.csv` | timestamp, beats per minute, data source | 日记录；方法未指定，保留来源 |
| `daily_heart_rate_variability.csv` | timestamp, average heart rate variability milliseconds, data source | 导出说明定义为睡眠 RMSSD；Apple 导入的泛 HRV 跳过 |
| `Daily Heart Rate Variability Summary*.csv` | timestamp, rmssd | 旧版明确 RMSSD，不转换 SDNN |
| `UserSleeps_*.csv` | sleep_id, sleep_start/end, minutes_asleep, sleep_last_updated, data_source, algorithm_version | 同一 session 用最新修订；每个醒来日期取最长观察 session |
| `sleep-*.json` | logId, startTime/endTime, minutesAsleep, mainSleep | 排除明确非主睡眠；每个醒来日期取最长 session |
| `steps_*.csv` | timestamp, steps, data source | 导出区间计数按当地日求和 |
| `steps-*.json` | dateTime, value | 区间计数；ISO 或旧版月/日/年时间 |

没有主睡眠标志的 CSV 不虚构主睡眠身份。“最长观察 session”不是所有小睡相加的每日总睡眠，也不计算睡眠质量、规律评分或深睡诊断。步数只代表导出区间之和，不证明全天佩戴或运动强度达标。午夜/旅行时区可能影响日期解释，需用户核对。

ISO 有偏移时间换算到用户选定的时区；无偏移的旧时间按该时区解释，并统计 assumed_local_timezone。JSON 与 CSV、不同 data source、不同算法保留不同流，**不相加、不拼接基线**。完全相同时间重复步数只算一次；无修订元数据的冲突日/日记录排除；睡眠同一修订冲突也排除。缺失日期不填零。

Apple 标记来源的 RHR、HRV、步数不进入 Fitbit 流。其他来源标签也不必然证明来自某台 Fitbit：一个入口只绑定用户声明的一台设备，`device_identity` 会标明此限制。若包内含多台无法区分的 Fitbit，不要建立合并基线；先取得可分离的数据。

诊断信息包含识别文件数、无效/冲突行数、跳过的其他来源和无时区时间数量。只评估解析完整性，不评估传感器准确度。非零计数需要核对；读取失败不是“没有健康变化”。未支持的文件不会被推测成新指标。

## 长期运行

`serve` / `watch` 每轮按更新的本地快照重新规划，默认只分析完成的昨天。过旧数据没有新的目标行动推送。上传是副本，替换 Downloads 中原 ZIP 不会更新已上传副本，需重新选择。建议长期使用自己更新的本地目录。

多台设备可勾选“添加另一个设备/入口”，分别选择路径、指标和授权。请保持同一本地代号；替换设备时用新的设备代号。UI 不是多人服务，不直接暴露到公网。
