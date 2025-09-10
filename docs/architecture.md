# 架构与组件

系统采用插件化与服务层分离设计：

- 接收器（receivers）: 负责外部事件接入（当前提供 QQ/NoneBot2 实现）
- 处理器（processors）: LLM 解析、HTML 渲染、图片渲染
- 发送器（publishers）: 发布到外部平台（QQ 空间等）
- 服务层（services）: 审核、投稿、通知等业务编排
- 核心（core）: 插件基类、数据库、模型、枚举

## 时序流程

1) QQ 私聊消息 -> `receivers.qq.QQReceiver` 接收并缓存
2) 创建 `Submission` 记录，等待 `processing.wait_time` 聚合多条消息
3) `processors.pipeline.ProcessingPipeline` 依次执行：
   - `LLMProcessor`: needpriv/safemsg/isover/segments
   - `HTMLRenderer`: 生成 HTML 并收集 links
   - `ContentRenderer`: 用 Playwright 渲染为图片
4) `NotificationService` 发送审核卡片到管理群，管理员下发指令
5) `AuditService` 根据指令更新状态、入暂存区或发布/评论/拉黑等
6) `SubmissionService` 批量或单发到各发布平台，并记录 `PublishRecord`

## 插件接口

参见 `core/plugin.py`：

- `ReceiverPlugin`: start/stop/handle_message/send_private_message/send_group_message
- `PublisherPlugin`: publish/batch_publish/check_login_status
- `ProcessorPlugin`: process

## 数据库模型

见 `core/models.py`：

- `Submission`: 投稿主表，状态、渲染结果、编号
- `AuditLog`: 审核日志
- `BlackList`: 黑名单
- `StoredPost`: 暂存待发
- `MessageCache`: 多条消息缓存
- `PublishRecord`: 发布记录

## 扩展点

- 新接收器：继承 `receivers.base.BaseReceiver`
- 新发送器：继承 `publishers.base.BasePublisher`
- 新处理器：继承 `core.plugin.ProcessorPlugin` 并接入 `ProcessingPipeline`

