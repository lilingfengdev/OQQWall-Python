# OQQWall-Python 使用指南

## 启动与停止

```bash
# 启动（Linux/macOS）
./start.sh

# 启动（Windows）
start.bat

# 或直接运行（DRIVER 在代码中自动设为 ~fastapi）
python main.py
```

按 `Ctrl+C` 可停止服务。

## 基本流程

1) 投稿：用户私聊机器人发送文字/图片。2 分钟（可配）内的多条消息会合并为同一投稿。
2) 自动处理：LLM 安全检查与分段、HTML 渲染、图片渲染、链接收集。
3) 审核：系统将渲染结果推送到管理群，管理员使用“@机器人 审核指令”处理。
4) 发布：通过的投稿进入暂存区，按时间表自动发送，或由管理员命令/CLI 触发发送。

配置项对应代码：`processors/pipeline.py`、`services/*`、`config/settings.py`。

## 群内审核与管理指令

请见 docs/COMMANDS.md，包含：

- 审核指令：是/否/匿/等/删/拒/立即/刷新/重渲染/扩列审查/评论/回复/展示/拉黑
- 全局管理：调出/信息/待处理/删除待处理/删除暂存区/发送暂存区/设定编号/自检/快捷回复管理/黑名单操作
- 私聊指令：#评论、#反馈

## CLI 命令

```bash
# 查看配置
python cli.py config

# 投稿
python cli.py list-submissions --status pending --limit 10
python cli.py audit 123 approve --comment "通过"
python cli.py audit 124 reject --comment "内容不合适"

# 黑名单
python cli.py blacklist-add 1234567890 default --reason "违规内容"
python cli.py blacklist-list
python cli.py blacklist-remove 1234567890 default

# 数据库
python cli.py db-init
python cli.py test-db

# 手动发送暂存区
python cli.py flush-posts --group default
```

## 常用配置（节选）

```yaml
# 定时发送
publishers:
  qzone:
    send_schedule: ["09:00", "12:00", "18:00", "21:00"]

# 多账号协同
account_groups:
  campus:
    main_account:
      qq_id: "1234567890"
      http_port: 3000
    minor_accounts:
      - qq_id: "9876543210"
        http_port: 3001

# 快捷回复
account_groups:
  default:
    quick_replies:
      "格式": "投稿格式：直接发送文字+图片即可"
      "时间": "每天 9/12/18/21 点发送"

# 水印/墙标
account_groups:
  default:
    watermark_text: "校园墙 · 2025"
    wall_mark: "OQQWall"
```

## 日志与健康检查

- 日志目录：`data/logs/`
- 实时查看：`tail -f data/logs/oqqwall_$(date +%Y-%m-%d).log`
- 健康检查：`curl http://localhost:8082/health`

## 备份与恢复

```bash
# 备份数据库
cp data/oqqwall.db data/oqqwall.db.backup

# 备份全部数据
tar czf backup_$(date +%Y%m%d).tar.gz data/

# 恢复
cp data/oqqwall.db.backup data/oqqwall.db
tar xzf backup_20240101.tar.gz
```

## 开发与扩展

- 新接入端：继承 `receivers/base.py` 的 `BaseReceiver`
- 新发布端：继承 `publishers/base.py` 的 `BasePublisher`
- 自定义处理：在 `processors/pipeline.py` 中挂接处理阶段

更多细节参见 docs/CONFIG.md 与源码注释。
