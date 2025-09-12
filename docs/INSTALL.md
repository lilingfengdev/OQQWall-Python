# OQQWall-Python 安装指南

## 系统要求

- Python 3.9+
- 4GB+ RAM（推荐）
- Chromium（用于渲染图片；通过 Playwright 安装，Docker 镜像已内置）
- OneBot v11 实现（推荐 NapCat）

## 快速安装

### 1. 克隆项目

```bash
git clone https://github.com/lilingfengdev/OQQWall-Python.git
cd OQQWall-Python
```

### 2. 手动安装（或使用一键脚本）

#### Linux/macOS（推荐）
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp config/config.example.yaml config/config.yaml
# 编辑 config/config.yaml（账号组、NapCat 端口、LLM 等）

# 初始化数据库
python cli.py db-init

# 安装 Playwright Chromium（首次）并启动
python -m playwright install chromium
./start.sh  # 或 python main.py
```

#### Windows
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

copy config\config.example.yaml config\config.yaml
REM 初始化数据库
python cli.py db-init

REM 启动
start.bat  REM 或 python main.py
```

### 3. 对接 NapCat / OneBot v11

在 NapCat（或任意 OneBot v11 实现）中配置“反向 WebSocket”连接到：

- ws://<你的主机>:8082/onebot/v11/ws

如在 `config.receivers.qq.access_token` 中设置了 Access Token，请在 NapCat 侧配置相同的 Token。

QQ 空间发布器会优先尝试通过 NapCat 本地 HTTP 接口拉取 cookies（需要在 `account_groups.*.main_account.http_port` 指定端口，并确保本地接口提供 `/get_cookies?domain=qzone.qq.com`）。

### 4. 健康检查

```bash
curl http://localhost:8082/health
```

## Docker 安装

### Docker Compose

```bash
docker-compose up -d
docker-compose logs -f
```

默认会挂载 `./config` 与 `./data`，并暴露 `8082` 端口。

### 单独使用 Docker

```bash
docker build -t oqqwall .
docker run -d \
  --name oqqwall \
  -p 8082:8082 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  -e LLM_API_KEY=your-api-key \
  oqqwall
```

## 推荐配置（节选）

完整配置详见 docs/CONFIG.md，以下为账号组与接收/发布端的关键项：

```yaml
account_groups:
  default:
    name: "默认组"
    manage_group_id: "123456789"
    main_account:
      qq_id: "1234567890"
      http_port: 3000
      http_token: ""
    minor_accounts: []

receivers:
  qq:
    enabled: true
    auto_accept_friend: true
    friend_request_window: 300
    access_token: ""   # 若启用 OneBot 鉴权

publishers:
  qzone:
    enabled: true
    max_attempts: 3
    batch_size: 30
    send_schedule: ["09:00", "12:00", "18:00", "21:00"]
```

## 常见问题（节选）

更多问题与解决方案见 docs/TROUBLESHOOTING.md。

- 数据库初始化失败：检查 `data/` 目录权限或路径是否存在。
- NapCat 连接失败：
  - 确认 NapCat 已运行且配置了反向 WS 到 `8082`；
  - 如启用鉴权，核对 Access Token；
  - 检查服务器防火墙与端口映射。
- LLM 调用失败：核对 `llm.provider` 与 `llm.api_key`，并检查网络。
- 图片渲染失败：执行 `python -m playwright install chromium` 或在 Docker 环境运行（镜像已内置）。

## 升级

```bash
# 备份数据
cp -r data data.backup

# 拉取最新代码
git pull

# 更新依赖
pip install -r requirements.txt --upgrade
```

重启服务后生效。
