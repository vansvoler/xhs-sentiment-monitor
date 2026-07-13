#!/bin/bash
# 存量偏题笔记清理。默认 dry-run 只统计；加 --apply 才真删。
#   bash scripts/purge_offtopic.sh          # 预览
#   bash scripts/purge_offtopic.sh --apply  # 执行
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run python -m src.maintenance.purge_offtopic "$@"
