# 安装与部署

## 系统要求

- Python 3.9+
- 4GB+ RAM
- Chrome/Chromium浏览器（用于渲染）
- NapCat/OneBot（QQ机器人框架）

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/lilingfengdev/OQQWall-Python.git
cd OQQWall-Python
```

### 2. 安装依赖

#### 手动安装
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -U pip
pip install -r requirements.txt
```

如需本地渲染图片，请安装 Playwright 浏览器驱动：

```bash
python -m playwright install chromium
```

### 3. 配置

1. 复制配置文件模板：
```bash
cp config/config.example.yaml config/config.yaml
```

2. 编辑 `config/config.yaml`，填写必要的配置：
   - LLM API密钥
   - QQ账号信息
   - 管理群ID
   - NapCat端口配置

3. （可选）创建环境变量文件：
```bash
cp .env.example .env
```

### 4. 启动 OneBot/NoneBot

1. 安装 NapCat 或其他 OneBot v11 实现
2. 使用 NoneBot2（FastAPI 驱动）。程序会设置 `DRIVER=~fastapi`
3. 启动 OneBot 实现后，运行本项目即可接收事件

### 5. 初始化数据库

```bash
python cli.py db-init
```

### 6. 启动服务

```bash
DRIVER=~fastapi python main.py
```

## Docker

### 使用Docker Compose

1. 配置环境变量：
```bash
cp .env.example .env
# 编辑.env文件，填写API密钥等
```

2. 启动服务：
```bash
docker-compose up -d
```

3. 查看日志：
```bash
docker-compose logs -f
```

### 手动构建运行

1. 构建镜像：
```bash
docker build -t oqqwall .
```

2. 运行容器：
```bash
docker run -d \
  --name oqqwall \
  -p 8082:8082 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  -e LLM_API_KEY=your-api-key \
  oqqwall
```

## 配置说明

### 账号组配置

```yaml
account_groups:
  group1:  # 组名
    name: "第一组"
    manage_group_id: "123456789"  # 管理群号
    main_account:
      qq_id: "1234567890"  # 主账号QQ
      http_port: 3000       # NapCat端口
      http_token: ""        # Napcat HTTP Token（若启用）
    minor_accounts:  # 副账号（可选）
      - qq_id: "9876543210"
        http_port: 3001
        http_token: ""
```

### LLM配置

支持的LLM提供商：
- **dashscope** (阿里云通义千问)
- **openai** (OpenAI GPT)

```yaml
llm:
  provider: dashscope
  api_key: sk-xxxxx  # API密钥
  text_model: qwen-plus-latest  # 文本模型
  vision_model: qwen-vl-max-latest  # 视觉模型
```

### 接收器配置

```yaml
receivers:
  qq:
    enabled: true
    auto_accept_friend: true  # 自动同意好友请求
    friend_request_window: 300
    access_token: ""  # 若启用 OneBot 鉴权
```

### 发送器配置

```yaml
publishers:
  qzone:
    enabled: true
    max_attempts: 3  # 失败重试次数
    batch_size: 30  # 批量发送数量
    send_schedule: ["09:00", "12:00", "18:00", "21:00"]  # 定时发送
```

## 故障排除

### 1. 数据库连接失败

检查数据目录权限：
```bash
chmod 755 data
```

### 2. NapCat连接失败

- 确认NapCat正在运行
- 检查端口配置是否正确
- 确认webhook地址配置正确

### 3. LLM调用失败

- 检查API密钥是否正确
- 确认账户余额充足
- 检查网络连接

### 4. 图片渲染失败

安装Chrome/Chromium：
```bash
# Ubuntu/Debian
sudo apt-get install chromium-browser

# CentOS/RHEL
sudo yum install chromium

# macOS
brew install chromium
```

## 升级

1. 备份数据：
```bash
cp -r data data.backup
```

2. 更新代码：
```bash
git pull
```

3. 更新依赖：
```bash
pip install -r requirements.txt --upgrade
```

4. 重启服务

## 支持

- 仓库: https://github.com/lilingfengdev/OQQWall-Python
- Issues: https://github.com/lilingfengdev/OQQWall-Python/issues
