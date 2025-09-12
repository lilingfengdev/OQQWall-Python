# QQ 空间发布器（QzonePublisher）

实现：`publishers/qzone/publisher.py`，API 封装见 `publishers/qzone/api.py`。

## 功能

- 自动加载 `data/cookies/qzone_<qq>.json` 的 cookies；
- cookies 无效时，尝试经 NapCat 本地 HTTP `/get_cookies?domain=qzone.qq.com` 拉取；
- 文本内容拼装：可配置是否包含编号/@投稿者/分段文本/链接列表；
- 图片处理：将各种格式统一转为 JPEG，避免 WebP 等不兼容；
- 批量发布支持轮询多个账号；
- 支持对已发布投稿追加评论。

## 配置

主配置 `publishers.qzone` 与覆盖文件 `config/publishers/qzone.yml` 合并：

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
    image_source: rendered   # rendered|chat|both
    include_segments: true
```

账号端口来源：`account_groups.*.(main_account|minor_accounts).http_port`。

## 常见问题

- 登录失效：检查 NapCat 本地接口是否可访问；确认 `http_token`（如配置）正确；
- 图片失败：确认图片路径/URL 可访问；
- @投稿者不生效：QQ 空间不保证 @ 成功且不会跨平台 @。

