#!/bin/bash

# 停止后端服务脚本

echo "停止小红书舆情监控系统..."

# 查找并杀掉Python进程
PIDS=$(pgrep -f "python main.py")

if [ -n "$PIDS" ]; then
    echo "找到进程: $PIDS"
    kill $PIDS
    echo "服务已停止"
else
    echo "未找到运行中的服务"
fi
