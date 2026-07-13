#!/bin/bash
# 孤儿词笔记清理（search_keyword 已不在监控词里）。默认 dry-run；加 --apply 真删。
#   bash scripts/purge_orphan_keywords.sh                        # 预览全部孤儿词
#   bash scripts/purge_orphan_keywords.sh --keyword yxt          # 预览定向清理
#   bash scripts/purge_orphan_keywords.sh --keyword yxt --apply  # 执行定向清理
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run python -m src.maintenance.purge_orphan_keywords "$@"
