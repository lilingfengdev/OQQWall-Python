#!/bin/bash

# OQQWall 启动脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          OQQWall-Python 启动脚本         ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo -e "${RED}错误: Python版本必须 >= 3.9，当前版本: $python_version${NC}"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source venv/bin/activate

# 安装/更新依赖
echo -e "${YELLOW}检查依赖...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 安装 Playwright 浏览器（Chromium）
echo -e "${YELLOW}安装 Playwright Chromium...${NC}"
python3 -m playwright install chromium >/dev/null 2>&1 || true

# 检查配置文件
if [ ! -f "config/config.yaml" ]; then
    echo -e "${YELLOW}配置文件不存在，创建默认配置...${NC}"
    cp config/config.example.yaml config/config.yaml 2>/dev/null || true
    echo -e "${RED}请编辑 config/config.yaml 配置文件后重新启动${NC}"
    exit 1
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}环境变量文件不存在${NC}"
    echo -e "${YELLOW}如需配置环境变量，请创建 .env 文件${NC}"
fi

# 创建必要的目录
mkdir -p data data/cache data/logs data/cookies

# 初始化数据库
echo -e "${YELLOW}初始化数据库...${NC}"
python3 cli.py db-init

# 启动参数处理
case "$1" in
    -d|--debug)
        echo -e "${YELLOW}以调试模式启动...${NC}"
        export DEBUG=true
        export LOG_LEVEL=DEBUG
        ;;
    -h|--help)
        echo "用法: $0 [选项]"
        echo "选项:"
        echo "  -d, --debug    调试模式"
        echo "  -h, --help     显示帮助"
        exit 0
        ;;
esac

# 启动主程序
echo -e "${GREEN}启动 OQQWall...${NC}"
export DRIVER=~fastapi
python3 main.py
