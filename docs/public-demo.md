# 公开报告演示：无需安装

任何人都可以在 GitHub 直接打开[完整合成健康报告](sample-health-report.md)、[设备与字段表](model-capabilities.md)、[方法与论文映射](report-methodology.md)和[新用户指引](start-here.md)。这些是公开阅读入口，无需运行程序。

## 交互演示

仓库包含独立的 [site/index.html](../site/index.html)。在 GitHub 文件页点击 **Download raw file**，保存为 `index.html`，然后用浏览器打开。页面内置合成数据，可切换设备与目标、查看记录充分/不足时的不同输出、体验反馈如何改变行动。没有依赖、后台服务或密钥。

它是体验说明，不运行生产分析器，不连接真实设备、不接受健康文件或密钥，也不会真的定时推送。示例数字固定展示；真实分析逻辑见 src/healthos/reports.py。

## 在线发布状态与维护

GitHub Pages 尚需仓库管理员首次在 **Settings → Pages → Source → GitHub Actions** 启用。发布地址只有部署成功、实际打开验证后才能当作在线入口。仓库写入 HTML 不等于网页已发布；未启用时，上面的 GitHub 报告和文件下载始终可用。

本仓库的 Public demo workflow 在每次 main 推送时校验并打包公开文件清单；检测到 Pages 已启用才部署。首次启用后，在 **Actions → Public demo → Run workflow** 发布，成功后的地址会显示在部署任务中。

公开站点由固定允许清单构建：`site/` 加公开 healthos-skill.json 与 llms.txt；配置实际站点 URL 后才生成 canonical 与 sitemap。不会部署私人工作目录、OAuth 凭证、模型密钥或健康记录。Pages 是静态展示；真实同步、LLM 调用和周期推送运行在用户自己的部署环境。

## 实际界面预览

![独立 HTML 合成体验页面](public-demo-ui.png)
