#!/bin/bash
# 笔记去重清理。默认 dry-run 只统计；加 --apply 才真删。
#   bash scripts/dedup_notes.sh          # 预览
#   bash scripts/dedup_notes.sh --apply  # 执行
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run python -m src.maintenance.dedup_notes "$@"
