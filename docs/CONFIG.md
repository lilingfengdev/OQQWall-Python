# 配置手册（CONFIG）

本文基于实际代码（`config/settings.py`、`utils/common.py` 等）整理，列出各配置块与关键字段。配置文件路径默认为 `config/config.yaml`，首次运行会自动生成默认配置。

支持使用 `config/publishers/<platform>.yml` 对指定发布端进行覆盖与扩展，覆盖优先级：主配置 < 覆盖文件。

## 顶层结构

```yaml
system: {}
server: {}
database: {}
redis: {}
queue: {}
llm: {}
processing: {}
receivers: {}
publishers: {}
audit: {}
account_groups: {}
```

## system（系统）

```yaml
system:
  debug: false           # 调试模式
  log_level: INFO        # 日志级别
  data_dir: ./data       # 数据目录
  cache_dir: ./data/cache
```

## server（服务端）

```yaml
server:
  host: 0.0.0.0
  port: 8082
  workers: 4
```

## database（数据库）

```yaml
database:
  type: sqlite
  url: sqlite+aiosqlite:///./data/oqqwall.db
  pool_size: 10
```

SQLite 会启用 WAL 等优化。首次启动会自动建表。

## redis（可选）

```yaml
redis:
  enabled: false
  host: localhost
  port: 6379
  db: 0
```

## queue（任务队列）

```yaml
queue:
  backend: AsyncSQLiteQueue   # AsyncSQLiteQueue | AsyncQueue | MySQLQueue
  path: data/queues           # Async* 后端的数据目录
  mysql:                      # MySQLQueue 所需连接参数
    host: 127.0.0.1
    port: 3306
    user: root
    password: ""
    database: oqqqueue
    table: oqq_tasks
```

用于定时发送的排队与串行消费。参见 `services/submission_service.py`。

## llm（大模型）

```yaml
llm:
  provider: dashscope         # dashscope | openai
  api_key: sk-xxxxx           # 支持 ${ENV_NAME} 从环境变量读取
  text_model: qwen-plus-latest
  vision_model: qwen-vl-max-latest
  timeout: 30
  max_retry: 3
```

`api_key` 可写成 `${LLM_API_KEY}`，由环境变量替换。

## processing（处理）

```yaml
processing:
  wait_time: 120              # 等待补充消息时间（秒）
  max_concurrent: 10
```

`wait_time` 会影响是否合并 2 分钟内消息为同一投稿。

## receivers（接入端）

目前内置 QQ 接入：`receivers.qq`（NoneBot2 + OneBot v11）。

```yaml
receivers:
  qq:
    enabled: true
    auto_accept_friend: true
    friend_request_window: 300
    access_token: ""          # 反向 WS/HTTP 鉴权 Token（可选）
```

启动后将以 FastAPI 驱动暴露 OneBot v11 接口（`DRIVER=~fastapi`）。

## publishers（发布端）

每个平台均支持以下通用控制字段（详见对应模型）：

- enabled: 是否启用
- max_attempts: 单条失败后的最大重试次数
- batch_size: 批量发布批次大小
- max_images_per_post: 单条发布最多图片数
- send_schedule: 定时发送时间数组（HH:MM 或 HH:MM:SS）
- publish_text: 是否发布正文文本
- include_publish_id: 文本中是否包含发布编号
- include_at_sender: 是否 @ 投稿者（平台支持的情况下）
- image_source: 图片来源 rendered|chat|both
- include_segments: 是否包含聊天分段文本

### qzone（QQ 空间）

```yaml
publishers:
  qzone:
    enabled: true
    max_attempts: 3
    batch_size: 30
    max_images_per_post: 9
    send_schedule: []
    publish_text: true
    include_publish_id: true
    include_at_sender: true
    image_source: rendered
    include_segments: true
```

QQ 空间 cookies 将存放于 `data/cookies/qzone_<qq>.json`。若失效，会尝试经 NapCat 本地 HTTP `/get_cookies?domain=qzone.qq.com` 重新拉取。

### bilibili（B 站）

```yaml
publishers:
  bilibili:
    enabled: false
    max_attempts: 3
    batch_size: 30
    max_images_per_post: 9
    send_schedule: []
    publish_text: true
    include_publish_id: true
    include_at_sender: false
    image_source: rendered
    include_segments: false
    accounts: {}              # 可显式配置 {account_id: {cookie_file: ...}}
```

cookies 文件默认读取 `data/cookies/bilibili_<account>.json`，需包含 `SESSDATA` 与 `bili_jct`/`csrf`。

### rednote（小红书）

```yaml
publishers:
  rednote:
    enabled: false
    max_attempts: 3
    batch_size: 20
    max_images_per_post: 9
    send_schedule: []
    publish_text: true
    include_publish_id: false
    include_at_sender: false
    image_source: rendered
    include_segments: false
    accounts: {}
    headless: true
    slow_mo_ms: 0
    user_agent: ""
```

cookies 需为 Playwright 兼容数组，默认 `data/cookies/rednote_<account>.json`。

## audit（审核）

```yaml
audit:
  auto_approve: false
  ai_safety_check: true
  sensitive_words: []
```

## account_groups（账号组）

```yaml
account_groups:
  default:
    name: "默认组"
    manage_group_id: "123456789"  # 审核管理群
    main_account:
      qq_id: "1234567890"
      http_port: 3000
      http_token: ""
    minor_accounts: []             # 副账号数组（同结构）
    max_post_stack: 1              # 达阈值自动批量
    max_images_per_post: 30
    send_schedule: []              # 组级计划（目前主要由各平台控制）
    watermark_text: ""            # 渲染水印文字
    wall_mark: "OQQWall"          # 渲染页底部标识
    friend_add_message: "你好，欢迎投稿"
    quick_replies: { }            # 群内自定义快捷回复
    allow_anonymous_comment: true # 启用 #评论 私聊指令
```

## 配置合并规则

- 读取主配置 `config/config.yaml` 后，再尝试加载 `config/publishers/<platform>.yml` 进行深度合并（覆盖同名字段）。
- 详见 `utils/common.py:get_platform_config`。

## 环境变量

- 可在 `.env` 或运行环境中设置，例如：`LLM_API_KEY`。
- `llm.api_key` 写成 `${LLM_API_KEY}` 即可从环境读取。

