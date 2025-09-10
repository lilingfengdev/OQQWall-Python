# 配置说明

本文说明 `config/config.yaml` 中的关键项。所有字段均有默认值，且支持通过环境变量覆盖（写为 ${ENV_NAME}）。

## 顶层结构

```yaml
system:
server:
database:
redis:
llm:
processing:
receivers:
publishers:
audit:
account_groups:
```

## system

- debug: 是否调试日志
- log_level: INFO/DEBUG 等
- data_dir: 数据目录，默认 ./data
- cache_dir: 缓存目录，默认 ./data/cache

## server

- host: 监听地址（默认 0.0.0.0）
- port: 监听端口（默认 8082）
- workers: 预留（NoneBot/FastAPI 驱动运行）

## database

- type: sqlite 或其它
- url: SQLAlchemy 连接串（默认 sqlite+aiosqlite:///./data/oqqwall.db）
- pool_size: 连接池大小

## redis（可选）

- enabled: 是否启用
- host/port/db: 连接参数

## llm

- provider: dashscope/openai
- api_key: 可写为 ${LLM_API_KEY}
- text_model/vision_model: 模型名称
- timeout/max_retry: 请求超时与重试

## processing

- wait_time: 合并消息等待秒数（默认 120）
- max_concurrent: 处理并发

## receivers

### receivers.qq

- enabled: 启用 QQ 接收器
- auto_accept_friend: 自动同意好友请求
- friend_request_window: 好友请求去重窗口秒
- access_token: OneBot 鉴权 token（如启用）

## publishers

### publishers.qzone

- enabled: 启用 QQ 空间发布
- publish_text: 是否发布正文（编号/@/评论/分段/链接）
- include_publish_id: 是否包含发布编号
- include_at_sender: 是否 @ 投稿者（非匿名时）
- image_source: rendered|chat|both，图片来源
- include_segments: 是否包含聊天分段文本
- send_schedule/max_attempts/batch_size/max_images_per_post: 任务控制

### publishers.bilibili（可选）

- enabled: 启用 B 站发送器
- 其他控制项与 qzone 对齐，便于统一
- accounts: 可声明账号与 cookie 文件
  - accounts.<account_id>.cookie_file: 指定 cookies 路径；未指定则默认 data/cookies/bilibili_<account_id>.json

详见：docs/bilibili.md

## audit

- auto_approve: 是否自动通过
- ai_safety_check: 是否启用 AI 安全检查
- sensitive_words: 违禁词列表

## account_groups

每个组定义一个管理群、主/副账号、编号与水印等：

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
    max_post_stack: 1
    max_images_per_post: 30
    send_schedule: []
    watermark_text: "校园墙 · 2024"
    friend_add_message: "你好，欢迎投稿"
    quick_replies:
      "格式": "投稿格式：直接发送文字+图片即可"
    allow_anonymous_comment: true
```

提示：可通过 `python cli.py config` 查看解析后的生效配置。

