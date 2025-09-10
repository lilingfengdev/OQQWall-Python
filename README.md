## OQQWall-Python 重构版

面向校园墙/树洞类运营的自动化系统。基于异步与插件化架构，提供投稿接收、AI处理、审核流、渲染出图与多平台发布能力。

### 功能亮点

- 插件化：接收器、处理器、发送器均可扩展
- 高并发：全链路异步，内置连接池与缓存
- AI 加持：文本/多模态解析、匿名与安全判断、分段生成
- 可运营：审核群指令、快捷回复、编号体系、批量/定时发送
- 易部署：一键脚本与 Docker 支持，健康检查就绪

### 技术栈

- FastAPI/NoneBot2（OneBot v11）
- SQLAlchemy Async + SQLite（可扩展 PostgreSQL）
- Pydantic + YAML 配置，支持环境变量
- Loguru、Click CLI、Playwright 渲染、aioqzone 发布

### 项目结构

```
OQQWall-Python/
├── config/                 配置系统（YAML/环境变量）
├── core/                   核心：数据库、模型、插件与枚举
├── receivers/              接收器（QQ/NoneBot2 实现）
├── processors/             处理管道（LLM、HTML、图片渲染）
├── publishers/             发送器（QQ空间、B站可扩展）
├── services/               服务层（审核/投稿/通知）
├── docs/                   文档（安装/使用/配置/扩展）
├── cli.py                  命令行工具
├── main.py                 主程序入口
└── Dockerfile/docker-compose.yml  部署支持
```

### 快速开始

```bash
# 1) 安装依赖（建议 Python 3.9+ 且使用虚拟环境）
pip install -r requirements.txt

# 2) 初始化配置
cp config/config.example.yaml config/config.yaml
# 将 llm.api_key、account_groups 等按实际情况填写

# 3) 初始化数据库
python cli.py db-init

# 4) 启动（确保设置 DRIVER=~fastapi 以启用 NoneBot2 FastAPI 驱动）
DRIVER=~fastapi python main.py
```

使用脚本一键启动：

```bash
chmod +x start.sh
./start.sh
```

### Docker 启动

```bash
# 本地构建并启动
docker-compose up -d

# 查看健康检查（/health 由 QQ 接收器提供）
curl http://localhost:8082/health
```

### CLI 常用命令

```bash
# 查看配置
python cli.py config

# 投稿与审核
python cli.py list-submissions --status pending --limit 10
python cli.py audit 123 approve --comment "好投稿"

# 黑名单
python cli.py blacklist-add 1234567890 default --reason "违规"
python cli.py blacklist-list
python cli.py blacklist-remove 1234567890 default

# 数据库
python cli.py db-init
python cli.py test-db
```

### 文档导航

- 安装与环境：docs/INSTALL.md
- 使用与审核流：docs/USAGE.md
- 配置说明：docs/configuration.md
- 架构与扩展：docs/architecture.md、docs/plugins.md、docs/services.md
- CLI 与 Docker：docs/cli.md、docs/docker.md
- B 站发布：docs/bilibili.md
- 迁移与排障：docs/migration.md、docs/troubleshooting.md、docs/faq.md

### 许可与致谢

- License: MIT
- 致谢原版 OQQWall 项目与各开源依赖的贡献者
