#!/bin/bash

# 停止后端服务脚本
# 注意：uvicorn reload 模式会 spawn 子进程持有端口，cmdline 不含 "python main.py"，
# 必须连同 8000 端口的监听进程一起杀，否则重启报 Address already in use。

echo "停止小红书舆情监控系统..."

PIDS=$(pgrep -f "python main.py")
PORT_PIDS=$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null)
ALL=$(echo "$PIDS $PORT_PIDS" | tr ' ' '\n' | sort -u | grep -v '^$')

if [ -n "$ALL" ]; then
    echo "找到进程: $ALL"
    kill $ALL 2>/dev/null
    echo "服务已停止"
else
    echo "未找到运行中的服务"
fi
