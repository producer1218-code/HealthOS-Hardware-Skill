# 公开仓库入口与发布

公开首页面向没有背景的访客；从 README → docs/start-here.md → 字段、接入、完整报告、方法与论文即可阅读，不要求先启动 localhost。

site/index.html 是独立合成演示；下载 HTML 即可在浏览器打开，不依赖 Python 或服务器。GitHub 不执行仓库 HTML；GitHub Pages 首次启用及部署状态见 [public-demo.md](public-demo.md)。不要在 README 声称尚未启用的站点已经可访问。

发布只包括公开源码、说明与合成数据；不包含私人记录、密钥、凭证或 SQLite。源码压缩包包含 site。Pages workflow 只上传 site/，未启用 Pages 时打包成功但跳过部署。核心 CI 继续在 Windows/Linux、Python 3.10/3.12 运行。
