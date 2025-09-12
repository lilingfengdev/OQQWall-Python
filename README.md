# OQQWall-Python （重构版）

校园墙自动运营系统，基于插件化架构构建：接入端（Receivers）、处理流水线（Processors）、发布端（Publishers），并配套服务层与 CLI 工具，帮助校园墙管理员高效、稳定地完成投稿收集、审核与多平台发布。

## 功能特性

- 插件化架构：易于扩展新的接入端与发布端
- 多平台发布：QQ 空间、B 站、小红书（可选）
- QQ 接入：NoneBot2 + OneBot v11（兼容 NapCat 等实现）
- AI 能力：LLM 文本处理与安全审查，自动渲染图片
- 审核流程：管理群内“@机器人 审核指令”即可完成全流程
- 定时/批量：按时间表自动发送或达阈值触发批量发布
- CLI 工具：投稿与黑名单管理、数据库检查等
- Docker 支持：一条命令快速拉起，内置健康检查

## 目录结构

```
OQQWall-Python/
├── config/                      # 配置与模型
│   ├── config.example.yaml      # 配置模板
│   ├── publishers/              # 各发布端的覆盖配置（可选）
│   └── settings.py              # Pydantic 配置模型与加载
├── core/
│   ├── database.py              # 异步数据库与会话管理
│   ├── enums.py                 # 枚举常量
│   ├── models.py                # SQLAlchemy 数据模型
│   └── plugin.py                # 插件与插件管理器
├── receivers/
│   ├── base.py                  # 接收器基类
│   └── qq/nonebot_receiver.py   # QQ 接收器（NoneBot2 + OneBot v11）
├── processors/
│   ├── llm_processor.py         # LLM 处理
│   ├── html_renderer.py         # HTML 渲染与链接收集
│   ├── content_renderer.py      # 图片渲染
│   └── pipeline.py              # 处理管道编排
├── publishers/
│   ├── base.py                  # 发布器基类与通用逻辑
│   ├── loader.py                # 动态发现与注册发布器
│   ├── qzone/                   # QQ 空间发布器
│   ├── bilibili/                # B 站发布器
│   └── rednote/                 # 小红书发布器
├── services/
│   ├── submission_service.py    # 投稿处理、定时与批量发布
│   ├── audit_service.py         # 审核指令处理
│   └── notification_service.py  # 通知下发（群/私聊）
├── utils/
│   ├── common.py                # 通用工具（去重、配置合并等）
│   └── json_util.py
├── docs/                        # 文档
├── cli.py                       # 管理 CLI（click）
├── main.py                      # 主程序入口
├── start.sh | start.bat         # 一键启动脚本
├── Dockerfile | docker-compose.yml
└── requirements.txt
```

## 快速开始

### 1) 安装依赖并准备配置

```bash
git clone https://github.com/lilingfengdev/OQQWall-Python.git
cd OQQWall-Python

python3 -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp config/config.example.yaml config/config.yaml
# 编辑 config/config.yaml（账号组、NapCat 端口、LLM 等）
```

必备环境：Python 3.9+、Chromium（通过 Playwright 安装；Docker 镜像已内置）、OneBot v11（推荐 NapCat）。

### 2) 运行

```bash
# Linux/macOS
./start.sh

# Windows
start.bat

# 首次需要安装 Playwright Chromium
python -m playwright install chromium

# 运行（DRIVER 将在代码中自动设为 ~fastapi）
python main.py
```

启动后服务监听在 `0.0.0.0:8082`，健康检查为 `GET /health`。

### 3) Docker 快速启动

```bash
docker-compose up -d
docker-compose logs -f
```

容器会暴露 `8082` 端口，并将 `./config` 与 `./data` 映射到容器内。

## NapCat / OneBot v11 对接

- 本项目内置 QQ 接入端，基于 NoneBot2 + OneBot v11。
- 推荐在 NapCat 中配置「反向 WebSocket」连接到：
  - `ws://<你的主机>:8082/onebot/v11/ws`
- 若在 `config.receivers.qq.access_token` 中设置了鉴权 Token，则需在 NapCat 侧配置相同的 Access Token。

QQ 空间发布器可通过 NapCat 本地 HTTP 接口自动拉取登录 cookies（需要启用 NapCat 本地接口，并在 `account_groups.*.main_account.http_port` 指明端口）。当检测到 cookies 失效时会尝试自动刷新。

## 常用命令（CLI）

```bash
# 初始化/自检
python cli.py db-init
python cli.py test-db

# 查看配置与投稿
python cli.py config
python cli.py list-submissions --status pending --limit 10

# 审核与黑名单
python cli.py audit 123 approve --comment "通过"
python cli.py blacklist-add 1234567890 default --reason "违规内容"
python cli.py blacklist-list
```

## 文档

- 安装部署: docs/INSTALL.md
- 使用说明: docs/USAGE.md
- 配置手册: docs/CONFIG.md
- 接入端（QQ/NapCat）: docs/RECEIVERS.md
- 审核与群内指令: docs/COMMANDS.md
- 发布端指南：
  - docs/publishers/QZONE.md
  - docs/publishers/BILIBILI.md
  - docs/publishers/REDNOTE.md
- 生产部署: docs/DEPLOYMENT.md
- 故障排查: docs/TROUBLESHOOTING.md

如需功能扩展（新增接入端/发布端/处理阶段），可参考 `receivers/base.py`、`publishers/base.py` 与 `processors/pipeline.py` 的实现。
