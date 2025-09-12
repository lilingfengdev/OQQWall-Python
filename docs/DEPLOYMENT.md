# 生产部署（Deployment）

## Docker（推荐）

- 使用 `docker-compose.yml` 一键部署：包含端口映射与数据卷挂载；
- 镜像内已安装 Chromium、中文字体，满足渲染需求；
- 健康检查：容器 `HEALTHCHECK` 基于 `GET /health`。

```bash
docker-compose up -d
docker-compose logs -f
```

## 裸机/系统服务

以 systemd 为例：

```
[Unit]
Description=OQQWall-Python Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/OQQWall-Python
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/OQQWall-Python/venv/bin/python /opt/OQQWall-Python/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

- 将仓库放置到 `/opt/OQQWall-Python`，创建 venv 并安装依赖；
- `systemctl daemon-reload && systemctl enable --now oqqwall.service`。

## 端口与网络

- 默认监听 `0.0.0.0:8082`；
- NapCat 反向 WS 需能连通该端口；
- 如启用鉴权，请在反向连接侧配置相同的 Token。

## 数据持久化

- 数据库：`data/oqqwall.db`
- 日志：`data/logs/`
- 渲染缓存与编号：`data/cache/`
- Cookies：`data/cookies/`

建议使用独立磁盘或备份策略，参见 docs/USAGE.md 的备份章节。

## 监控与日志

- 健康检查：`curl http://localhost:8082/health`
- 实时日志：`tail -f data/logs/oqqwall_$(date +%Y-%m-%d).log`

## 安全建议

- 将配置文件与 cookies 文件权限收紧（600/700）；
- 定期更新依赖与镜像；
- 限制管理群成员与指令权限；
- 设置敏感词与 AI 审查；
- 定期备份 `data/`。

