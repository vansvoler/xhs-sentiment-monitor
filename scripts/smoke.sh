#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

assert_http_ok() {
  local url=$1
  local label=$2

  if curl -fsS "$url" >/dev/null; then
    echo "OK   $label"
    return 0
  fi

  echo "FAIL $label -> $url"
  return 1
}

assert_json_contains() {
  local url=$1
  local expected=$2
  local label=$3

  if curl -fsS "$url" | grep -q "$expected"; then
    echo "OK   $label"
    return 0
  fi

  echo "FAIL $label -> 缺少关键字: $expected"
  return 1
}

echo "运行本地 smoke test..."

assert_http_ok "http://localhost:3000/dashboard" "前端 dashboard 可访问"
assert_json_contains \
  "http://localhost:8000/api/intel/overview" \
  "\"sections\"" \
  "后端 overview 返回分区数据"
assert_json_contains \
  "http://localhost:8000/api/intel/sources/university_site/sync-status" \
  "\"source_key\":\"university_site\"" \
  "大学官网同步状态接口可用"

echo "Smoke test 通过。"
