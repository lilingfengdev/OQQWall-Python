# 接入端（Receivers）

当前内置 QQ 接入端，基于 NoneBot2 + OneBot v11（适配 NapCat 等实现）。核心代码：`receivers/qq/nonebot_receiver.py`。

## 运行架构

- 服务启动后，NoneBot2 使用 FastAPI 作为驱动（`DRIVER=~fastapi`）。
- 暴露 OneBot v11 接口路径，如反向 WebSocket：`/onebot/v11/ws`。
- 接收的私聊消息会被缓存并在 `processing.wait_time` 内合并为单个投稿。
- 群消息默认不创建投稿，仅解析“@机器人 指令”。

## NapCat / OneBot 对接

在 NapCat 配置反向 WS 到 OQQWall 服务：

- ws://<你的主机>:8082/onebot/v11/ws

如设置了 `receivers.qq.access_token`，需在 NapCat 侧配置相同 Token。

## 自动同意好友与抑制策略

- `auto_accept_friend: true` 将自动通过好友请求。
- 对一定时间窗口内重复文本进行抑制，避免误触发重复投稿。
- 好友请求文本会短期加入抑制列表，避免刚添加好友即立刻触发投稿。

## 撤回事件

- 默认开启“好友撤回后，尝试删除对应缓存消息”的逻辑，以避免合并入新投稿。

## 黑名单

- 在建稿前会查询 `BlackList` 表，命中则拒绝建稿。
- 群内可用“拉黑/取消拉黑/列出拉黑”指令管理，或使用 CLI。

## 健康检查

- `GET /health` 返回 JSON 状态。

