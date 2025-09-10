# 迁移指南（从旧版 OQQWall）

使用 `migrate.py` 将旧版数据迁移至重构版。

```bash
python migrate.py /path/to/old/OQQWall
```

流程：
- 转换老配置 -> 生成 `config/config.yaml`
- 迁移数据库：sender/blacklist 等表
- 迁移 cookies 与编号文件

迁移后执行：
```bash
python cli.py db-init
DRIVER=~fastapi python main.py
```