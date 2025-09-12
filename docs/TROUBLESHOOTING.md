# 故障排查（Troubleshooting）

## 数据库问题

- 初始化失败或连接异常：
  - 确认 `data/` 目录存在且可写；
  - 路径中不要包含不可访问的上级目录；
  - 运行 `python cli.py test-db` 自检；
  - 若升级后异常，备份 `data/oqqwall.db` 并回滚。

## NapCat / OneBot 连接问题

- 无法连接或无事件推送：
  - 确认 NapCat 已启动并配置反向 WS 到 `ws://<host>:8082/onebot/v11/ws`；
  - 若启用鉴权，确认 Access Token 一致；
  - 检查服务器防火墙与端口映射；
  - 查看应用日志 `data/logs/`。

## QQ 空间登录/发布问题

- 登录失效：
  - 检查 NapCat 本地 HTTP `/get_cookies?domain=qzone.qq.com` 是否可用；
  - `account_groups.*.main_account.http_port` 与 `http_token`（如使用）是否正确；
  - 删除无效 cookie 文件后重试（将触发重新拉取）。
- 图片无法上传：
  - 确认图片路径/URL 可访问；
  - 本地文件推荐使用 `file:///绝对路径` 形式；
  - 项目会自动转换为 JPEG，个别异常将回退原图。

## B 站 / 小红书问题

- Cookie 无效或过期：
  - B 站需 `SESSDATA` 与 `bili_jct`/`csrf`；
  - 小红书需 Playwright 兼容 cookies 数组，可用登录脚本获取；
  - 文件格式必须是合法 JSON。

## LLM/渲染问题

- API 失败：检查网络与 `llm.provider`、`llm.api_key`；
- 渲染空白：确认已执行 `python -m playwright install chromium` 安装浏览器（Docker 镜像已内置）。

## 常用排查命令

```bash
# 健康检查
curl http://localhost:8082/health

# 端口占用
ss -tlnp | grep 8082 || netstat -tlnp | grep 8082

# 日志
ls -l data/logs/
tail -f data/logs/oqqwall_$(date +%Y-%m-%d).log
```

