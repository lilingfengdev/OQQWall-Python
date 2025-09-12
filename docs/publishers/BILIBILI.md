# B 站发布器（BilibiliPublisher）

实现：`publishers/bilibili/publisher.py`，API 封装见 `publishers/bilibili/api.py`。

## 功能

- 读取 cookies：`data/cookies/bilibili_<account>.json` 或在 `publishers.bilibili.accounts` 指定；
- 登录检查：基于 Credential/接口校验；
- 发布图文动态（专栏/视频不在此发布器范围内）；
- 批量发布按账号轮询；
- 支持为已发布投稿追加评论（通过记录的 `dynamic_id`）。

## 配置

```yaml
publishers:
  bilibili:
    enabled: true
    max_attempts: 3
    batch_size: 30
    max_images_per_post: 9
    send_schedule: []
    publish_text: true
    include_publish_id: true
    include_at_sender: false
    image_source: rendered
    include_segments: false
    accounts:
      myacc:
        cookie_file: data/cookies/bilibili_myacc.json
```

cookies 至少包含 `SESSDATA` 与 `bili_jct`/`csrf`。

## 常见问题

- Cookie 无效：重新抓取浏览器登录态，或确保文件 JSON 格式正确；
- 图片上传失败：检查网络与图片大小/格式；
- @ 投稿者：B 站不支持通过 QQ 号直接 @，此项默认关闭。

