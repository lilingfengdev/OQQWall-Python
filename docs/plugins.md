# 插件开发

## 接收器（Receiver）

基类：`receivers/base.py: BaseReceiver`

关键点：
- `start/stop` 启停生命周期
- `process_message` 通用建稿逻辑（缓存、合并、建稿触发）
- `set_message_handler/set_friend_request_handler` 注入回调
- 发送消息：`send_private_message`/`send_group_message`

现有实现：`receivers/qq/nonebot_receiver.py: QQReceiver`

## 发送器（Publisher）

基类：`publishers/base.py: BasePublisher`

能力：
- `publish_submission`/`batch_publish_submissions` 封装发布流程
- `prepare_content` 根据配置生成文案（编号/@/评论/分段/链接）
- `record_publish` 记录发布结果并更新状态

示例：`publishers/qzone/publisher.py: QzonePublisher`

## 处理器（Processor）

基类：`core/plugin.py: ProcessorPlugin`

管道：`processors/pipeline.py`

默认处理器：
- `LLMProcessor`：文本/多模态解析
- `HTMLRenderer`：聊天样式 HTML + 链接收集
- `ContentRenderer`：Playwright 截图

