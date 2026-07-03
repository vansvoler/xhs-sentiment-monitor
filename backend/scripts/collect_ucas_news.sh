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

python - <<'PY'
import asyncio

from src.services.intel_ingest import run_ucas_news_sync_job

count = asyncio.run(run_ucas_news_sync_job())
print(f"同步完成，写入 {count} 条 UCAS 新闻。")
PY
