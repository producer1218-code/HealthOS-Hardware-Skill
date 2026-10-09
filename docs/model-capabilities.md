# v0.6 live/report route update

For a Fitbit Air user, start with [Google Health connection](google-health-connect.md). In addition to the export fields below, experimental google-health-api and google-health-json readers now parse Fitbit daily RHR, daily-average RMSSD and processed main-sleep duration. They do not parse live steps, SpO2 or temperature. Google project eligibility and OS-encrypted storage are required for live access; no real-account/device verification has been completed. The original table remains the export/catalog view, not proof of live model support.

# 按型号查：能测什么、能取到什么、当前代码能读什么

研究快照：2026-10-08。这里的 20 行是**代表型号、型号组或平台**，不是 20 款已适配设备。请先区分三件事：公开资料称设备有传感器、用户产品会显示估算指标、第三方软件在许可下可取得的数据。只有“本仓库实际可读取”列列出的字段已有离线解析代码；具体型号/地区/固件仍需样例导出确认。每行来源链接可能只证明产品或数据接入的一部分，不能单独证明该行所有传感器、字段和准确性。

| 型号 / 平台 | 对外宣称的信号 | 用户端指标 | 本仓库实际可读取 | 证据 |
| --- | --- | --- | --- | --- |
| Apple Watch Series 12 | optical HR; ECG; SpO2; wrist temperature; motion | HR; HRV; respiration; sleep; ECG; activity | apple-health-xml: heart_rate_bpm, resting_heart_rate_bpm, hrv_sdnn_ms, spo2_pct, skin_temp_c | [原始来源](https://www.apple.com.cn/apple-watch-series-12/specs/) |
| WHOOP 5.0 and MG | optical HR; motion; temperature; MG ECG | HR; HRV; sleep; SpO2; Recovery; Strain | whoop-v2-json: resting_heart_rate_bpm, hrv_rmssd_ms, spo2_pct, skin_temp_c, sleep_minutes, respiratory_rate_bpm | [原始来源](https://developer.whoop.com/api/) |
| Google Fitbit Air | optical HR; red/IR SpO2; temperature; accelerometer; gyro | HR; HRV; sleep; activity; skin temperature trend | fitbit-takeout：RHR、明确 RMSSD、睡眠、步数；取决于实际导出，未逐型号验证；无实时/OAuth | [官方导出说明](https://support.google.com/googlehealth/answer/14236615) |
| Oura Ring V2 API account | optical PPG; temperature; motion | HR; HRV; sleep; readiness; temperature deviation | 尚无适配器 | [原始来源](https://cloud.ouraring.com/docs/) |
| Garmin Connect Health API devices | optical HR; SpO2; motion; by model more | HR; sleep; stress; Pulse Ox; Body Battery; respiration; BP where supported | 尚无适配器 | [原始来源](https://developer.garmin.com/gc-developer-program/health-api/) |
| Zepp/Amazfit Helio Strap | PPG; accelerometer; gyro; temperature | HR; HRV; SpO2; sleep; stress; BioCharge | 尚无适配器 | [原始来源](https://au.amazfit.com/products/helio-strap) |
| Huawei Band 11 | optical HR; 9-axis motion; ambient light | HR; SpO2; sleep; activity; stress | 尚无适配器 | [原始来源](https://consumer.huawei.com/cn/wearables/band11/specs/) |
| Huawei Watch D2 | optical; motion; cuff pressure sensor and pump | cuff blood pressure; wearable metrics | 尚无适配器 | [原始来源](https://consumer.huawei.com/cn/wearables/watch-d2/) |
| Xiaomi Smart Band 10 | PPG; motion | HR; SpO2; sleep; activity; stress estimate | 尚无适配器 | [原始来源](https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2331) |
| OPPO Watch X2 | optical HR; SpO2; ECG; wrist temperature; motion | HR; SpO2; ECG; sleep; respiratory insights | 尚无适配器 | [原始来源](https://www.opposhop.cn/cn/web/products/32731.html) |
| vivo WATCH 5 | optical HR/SpO2; motion; geomagnetic; light | HR; SpO2; sleep; stress; activity | 尚无适配器 | [原始来源](https://www.vivo.com.cn/vivo/param/vivowatch5) |
| Samsung Galaxy Ring and Galaxy Watch | not verified by this project | not verified by this project | 尚无适配器 | 待核实 |
| Withings ScanWatch and sleep devices | not verified by this project | not verified by this project | 尚无适配器 | 待核实 |
| Ultrahuman Ring Air | not verified by this project | not verified by this project | 尚无适配器 | 待核实 |
| Veepoo JH58 customized project | green PPG; accelerometer | project dependent | 尚无适配器 | [原始来源](https://github.com/HBandSDK/Android_Ble_SDK/wiki/VeepooSDK-Android-API-Document) |
| Polar H10 and Verity Sense | H10 ECG; Verity optical and motion | HR; model-specific streams | 尚无适配器 | [原始来源](https://github.com/polarofficial/polar-ble-sdk) |
| EmotiBit Research wearable | PPG; EDA; temperature; motion | research signals; interpretation built by developer | 尚无适配器 | [原始来源](https://www.emotibit.com/) |
| RingConn Gen 2 | hardware signals not independently verified here | vendor markets HR; HRV; SpO2; skin temperature; sleep; steps | 尚无适配器 | [原始来源](https://ringconn.com/products/ringconn-gen-2) |
| Looki L1 | vendor markets camera; microphones; motion | vendor markets lifelogs; reminders; video summaries | 尚无适配器 | [原始来源](https://www.looki.ai/) |
| AI recorder class other neck and lapel AI pendants | product-dependent; verify with vendor | transcripts or summaries where verified | 尚无适配器 | 待核实 |

## 如何使用

- `python -m healthos models --query "WHOOP"`：查看完整型号记录，包括数据授权路径与访问等级。
- `python -m healthos plan --profile examples/user_profile.json --output demo-output/user-plan.json`：把诉求与所选型号映射到“本仓库可读/暂不可读”的指标。
- [设备接入分级](data-access-playbook.md)解释 A 用户导出、B OAuth、C 合作 API、D 原始信号 SDK 的许可与工程差异。
- 若本仓库没有适配器，就先取得**允许使用的样例导出**并验证字段，再编写适配器；不要把厂商页面显示的分数直接当成开放 API 字段。
- Fitbit/Google 的开发者接入处于迁移期，[Google 官方页面](https://developers.google.com/health)显示新项目暂未开放接入，并写明旧 Fitbit Web API 的 2026-10-30 关闭计划；采购或开发前重新核对。
