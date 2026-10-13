# 部署与本机运行

上游：ErBharatMalhotra/open-source-ai-radar，MIT 许可。
安装使用的上游提交：`60d3dcb94ee4dceb786eb8f094cae6137d517eb4`。

- GitHub 仓库：https://github.com/papaoo/open-source-ai-radar
- GitHub Pages：https://papaoo.github.io/open-source-ai-radar/
- Vercel 云端：https://open-source-ai-radar.vercel.app/
- Vercel：`dingbei/open-source-ai-radar`，Hobby 免费套餐。
- 本机：http://127.0.0.1:4321/
- 本机启动：在项目目录运行 `powershell -File scripts/start-local.ps1`
- 本机停止：`powershell -File scripts/stop-local.ps1`

## 构建

```powershell
npm ci --prefix web
npm run build --prefix web
node scripts/copy-api.mjs
```

Node.js 24，Python 环境位于 `.venv`。运行时文件、数据库、日志和凭据不进入版本控制。
2026-10-13 已修复依赖审计发现的问题，npm audit 为 0 项漏洞。
网站采用静态页面，`vercel.json` 在云端安装、构建并复制 API 数据。
`SITE_URL` 与 `BASE_PATH` 可以覆盖站点地址和路径；Vercel 自动使用生产域名。

## 数据来源与更新

初次部署使用上游提交中自带的公开 JSON 快照：9,171 个项目，导出时间为 2026-10-13 07:03（北京时间）。
页面可以访问不等于已启动持续采集。独立 Fork 的采集工作流必须成功启用、运行，并与部署连接验证后，才能宣称自动更新。
原版发现与处理任务使用 GitHub Actions；可选 Groq 分类需要自行配置对应 Secret。
当前设置没有添加模型密钥或付费服务。

## Windows 文件名大小写

上游存在仅大小写不同的重复路径，Windows 普通工作区不能同时表示这些路径。
刚 clone 后部分 `data/exports/projects/*.json` 显示差异即源于此。本次未将这些数据差异提交。
不要使用 `git add .` 混入这些变化；使用明确的文件路径提交自己的修改。
Linux 云端从 GitHub 构建可以保留全部路径。

## 小体积上传备用方式

初次直接上传大量文件时，本机 Vercel CLI 出现内存不足。
`scripts/package-vercel.py` 使用 Git 原始树和明确列出的部署修改生成压缩包，保留全部大小写路径，避免上传本机私有文件。
GitHub Pages 使用本仓库的 Deploy Website 工作流，从 main 构建；需在仓库 Pages 设置中将来源设为 GitHub Actions。
修改站点、脚本或数据后推送会触发该工作流，也可手动运行。
Vercel 初次发布成功；当前账户已经关联 GitHub 用户 papaoo，需让 Vercel GitHub App 获得本仓库访问权限后连接项目。
