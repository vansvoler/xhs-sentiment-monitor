#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
BACKEND_LOG="$LOG_DIR/backend-dev.log"
FRONTEND_LOG="$LOG_DIR/frontend-dev.log"
# 探活用 /health（后端自带、不随业务路由增删而失效），
# 别指向业务接口——分支上功能没做完时会误判后端已死并连带杀掉前端。
BACKEND_URL="http://localhost:8000/health"
FRONTEND_URL="http://localhost:3000/dashboard"

mkdir -p "$LOG_DIR"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  local exit_code=$?

  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi

  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi

  wait >/dev/null 2>&1 || true
  exit "$exit_code"
}

wait_for_url() {
  local url=$1
  local label=$2
  local attempts=${3:-60}
  local delay_seconds=${4:-1}
  local attempt=1

  while [ "$attempt" -le "$attempts" ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay_seconds"
    attempt=$((attempt + 1))
  done

  echo "错误: $label 未在预期时间内就绪: $url"
  return 1
}

print_failure_logs() {
  echo
  echo "最近后端日志:"
  tail -n 20 "$BACKEND_LOG" 2>/dev/null || true
  echo
  echo "最近前端日志:"
  tail -n 20 "$FRONTEND_LOG" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "启动后端..."
(
  cd "$ROOT_DIR/backend"
  bash scripts/dev.sh
) >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo "启动前端..."
(
  cd "$ROOT_DIR/frontend"
  bash scripts/dev.sh
) >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

if ! wait_for_url "$BACKEND_URL" "后端" 60 1; then
  print_failure_logs
  exit 1
fi

if ! wait_for_url "$FRONTEND_URL" "前端" 60 1; then
  print_failure_logs
  exit 1
fi

echo
echo "开发环境已启动:"
echo "  Dashboard: $FRONTEND_URL"
echo "  Backend API: http://localhost:8000/docs"
echo "  后端日志: $BACKEND_LOG"
echo "  前端日志: $FRONTEND_LOG"
echo
echo "按 Ctrl-C 同时关闭前后端。"

while true; do
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo "错误: 后端进程已退出。"
    print_failure_logs
    exit 1
  fi

  if ! kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    echo "错误: 前端进程已退出。"
    print_failure_logs
    exit 1
  fi

  sleep 2
done
