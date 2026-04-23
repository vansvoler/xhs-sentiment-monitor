#!/bin/bash

# 开发环境启动脚本

echo "启动开发环境..."

# 进入虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "错误: 虚拟环境不存在，请先运行 scripts/setup.sh"
    exit 1
fi

# 启动服务（开发模式）
echo "启动FastAPI开发服务器..."
python main.py
