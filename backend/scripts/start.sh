#!/bin/bash

# 启动后端服务脚本

echo "启动小红书舆情监控系统..."

# 进入虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "错误: 虚拟环境不存在，请先运行 scripts/setup.sh"
    exit 1
fi

# 检查MongoDB
if ! pgrep -x mongod > /dev/null; then
    echo "警告: MongoDB未运行，请先启动MongoDB"
fi

# 创建日志目录
mkdir -p logs

# 启动服务
echo "启动FastAPI服务..."
nohup python main.py > logs/server.log 2>&1 &

echo "服务已启动，日志输出到 logs/server.log"
echo "访问 http://localhost:8000 查看API文档"
