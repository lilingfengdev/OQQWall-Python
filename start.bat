@echo off
REM OQQWall Windows启动脚本

echo ╔═══════════════════════════════════════════╗
echo ║          OQQWall-Python 启动脚本         ║
echo ╚═══════════════════════════════════════════╝

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请安装Python 3.9+
    pause
    exit /b 1
)

REM 创建虚拟环境（如果不存在）
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装/更新依赖
echo 检查依赖...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt >nul

REM 安装 Playwright 浏览器（Chromium）
echo 安装 Playwright Chromium...
python -m playwright install chromium >nul 2>&1

REM 检查配置文件
if not exist "config\config.yaml" (
    echo 配置文件不存在
    echo 请创建并编辑 config\config.yaml 配置文件后重新启动
    pause
    exit /b 1
)

REM 创建必要的目录
if not exist "data" mkdir data
if not exist "data\cache" mkdir data\cache
if not exist "data\logs" mkdir data\logs
if not exist "data\cookies" mkdir data\cookies

REM 初始化数据库
echo 初始化数据库...
python cli.py db-init

REM 启动主程序
echo 启动 OQQWall...
set DRIVER=~fastapi
python main.py

pause
