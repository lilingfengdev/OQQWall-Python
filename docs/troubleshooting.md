# 故障排除

## 数据库问题
- 确保 `data/` 可写：`chmod 755 data`
- 首次运行执行：`python cli.py db-init`

## QQ 接收/发送问题
- 确认 NapCat/OneBot v11 运行正常
- 如启用鉴权，确保 `receivers.qq.access_token` 一致
- 群指令需要 @ 机器人且管理员/群主权限

## LLM 调用失败
- 检查 `llm.api_key`/余额/网络
- 暂时失败时系统会回退默认判定

## 图片渲染失败
- 安装 Chromium 与 Playwright 驱动：`python -m playwright install chromium`
- 服务器缺少字体可安装 `fonts-noto-cjk`

## QQ 空间登录
- 系统使用 cookies（`data/cookies/qzone_<qq>.json`）与 gtk 检查
- 可通过 NapCat 本地接口拉取 qzone.qq.com 域 cookies（参见 QzonePublisher 登录逻辑）

## 健康检查
- 访问 `http://localhost:8082/health`