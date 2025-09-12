# 小红书发布器（RedNotePublisher）

实现：`publishers/rednote/publisher.py`，API 封装见 `publishers/rednote/api.py`。

## 功能

- 使用 Playwright 自动化发布图片笔记；
- 读取 Playwright 兼容 cookies（数组格式）；
- 标题取正文首行（最多 30 字），正文为剩余文本；
- 批量发布支持轮询账号；
- 支持为已发布投稿追加评论（需要发布结果记录 URL）。

## 配置

```yaml
publishers:
  rednote:
    enabled: true
    max_attempts: 3
    batch_size: 20
    max_images_per_post: 9
    send_schedule: []
    publish_text: true
    include_publish_id: false
    include_at_sender: false
    image_source: rendered
    include_segments: false
    accounts:
      myacc:
        cookie_file: data/cookies/rednote_myacc.json
    headless: true
    slow_mo_ms: 0
    user_agent: ""
```

cookies 文件应为 Playwright `storageState` 兼容的 cookies 数组（`[{name, value, domain, ...}]`）。

## 常见问题

- 需先通过登录工具获取 cookies：`python rednote_login_tool.py`；
- 发布失败：检查 cookies 是否过期、Chromium 可用性，以及图片数量/大小限制；
- 评论失败：需要发布结果中包含可访问的笔记 URL。

