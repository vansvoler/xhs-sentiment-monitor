#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -d ".venv" ]; then
  source .venv/bin/activate
else
  echo "错误: 虚拟环境不存在，请先同步 backend 依赖。"
  exit 1
fi

python -m src.collectors.intel_source_probe "$@"
