#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if command -v uv >/dev/null 2>&1; then
  uv run --extra dev pytest "$@"
  exit
fi

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python -m pytest "$@"
