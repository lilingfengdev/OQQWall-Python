# CLI 命令

```bash
# 配置
python cli.py config

# 投稿
python cli.py list-submissions --status pending --limit 10
python cli.py audit <id> approve --comment "ok"
python cli.py audit <id> reject --comment "不合适"

# 黑名单
python cli.py blacklist-add <qq> <group> --reason "违规"
python cli.py blacklist-list
python cli.py blacklist-remove <qq> <group>

# 数据库
python cli.py db-init
python cli.py test-db

# 手动发送（暂存）
python cli.py flush-posts --group <group>
```

