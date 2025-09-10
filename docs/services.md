# 服务层说明

## 审核服务 `services/audit_service.py`

- 命令表：是/否/匿/等/删/拒/立即/刷新/重渲染/扩列审查/评论/回复/展示/拉黑
- `approve`：赋予发布编号、入暂存区
- `approve_immediate`：通过后尝试立即发布
- `toggle_anonymous`：切换匿名并重渲染
- `rerender/refresh/hold`：重处理与等待
- `blacklist`：写入黑名单并删除投稿
- `add_comment/reply_to_sender`：评论与私聊回复
- `quick_reply`：根据账号组快捷键回复投稿者

## 投稿服务 `services/submission_service.py`

- `create_submission`：创建投稿并异步处理
- `process_submission`：合并消息 -> 管道处理 -> 通知审核
- `publish_stored_posts`：批量发布所有平台
- `publish_single_submission`：单条发布，成功后移出暂存
- `clear_stored_posts`：清空暂存并回滚编号

## 通知服务 `services/notification_service.py`

- 管理群通知与图片发送（按链接/file:// 适配 CQ 码）
- 私聊通知（通过 QQ 接收器发送）
- 审核提示卡片（包含内部编号、AI 判定摘要）

