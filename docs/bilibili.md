# Bilibili 发布说明

本页介绍如何启用 B 站图文动态发布，包括登录（cookies）、配置与使用。

## 前置条件

- 已安装依赖：`bilibili-api-python`（requirements.txt 已包含）
- 启用发送器：`publishers.bilibili.enabled: true`

## 登录方式（cookies 文件）

系统不包含自动登录流程，依赖外部提供的 cookies 文件。至少需要：
- SESSDATA
- bili_jct（或等价 csrf）

可选但建议：
- DedeUserID
- buvid3

支持两种 cookies 文件格式：

1) 字典格式（推荐）：
```json
{
  "SESSDATA": "xxx",
  "bili_jct": "xxx",
  "DedeUserID": "123456",
  "buvid3": "xxx"
}
```

2) 浏览器导出的数组格式：
```json
[
  {"name": "SESSDATA", "value": "xxx"},
  {"name": "bili_jct", "value": "xxx"},
  {"name": "DedeUserID", "value": "123456"}
]
```

将文件保存为以下任一位置：
- 指定路径：在配置中为每个账号设置 cookie_file
- 默认路径：`data/cookies/bilibili_<account_id>.json`

> 提示：可在浏览器登录 `www.bilibili.com` 后，从开发者工具 Application/Storage 中导出 Cookies，或使用浏览器扩展导出。

## 配置示例

在 `config/config.yaml` 中启用并配置：

```yaml
publishers:
  bilibili:
    enabled: true
    publish_text: true
    include_publish_id: true
    include_segments: false
    image_source: rendered   # rendered|chat|both
    max_images_per_post: 9
    accounts:
      "123456":                       # 建议使用 B 站 uid 作为 account_id
        cookie_file: data/cookies/bilibili_123456.json
```

说明：
- accounts 中的 key 为本系统内部的账号标识（account_id）。建议设置为对应 B 站 uid 便于识别。
- 未显式配置 accounts 时，将尝试镜像 QQ 账号 ID 对应的默认路径 `data/cookies/bilibili_<qq_id>.json`。
- 本系统不会自动刷新 B 站登录态；当 cookies 过期时，请更新上述文件。

## 使用与发布

- 审核通过（“是”）后，投稿会进入暂存区；达到批量条件或执行“发送暂存区”时，若启用 B 站发送器，将同步发布到 B 站。
- “立即” 指令会尝试即时发布单条投稿（若平台启用且 cookies 可用）。
- 批量发布时，若配置了多个 B 站账号，将轮询账号进行发布。

## 登录状态检查

- 系统在发布前会轻量检查 SESSDATA/bili_jct 是否存在。
- 如发布失败，请查看运行日志确认 cookies 是否过期或被风控。

## 常见问题

- 发布报错/无权限：更新 cookies 文件；确认 SESSDATA 与 bili_jct 有效。
- 图片过多：受 max_images_per_post 限制，超出部分会被忽略。
- @ 投稿者：B 站不支持通过 QQ 号直接 @，默认不添加 @ 文本。