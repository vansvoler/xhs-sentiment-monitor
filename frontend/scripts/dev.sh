#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
npm run dev 2>&1 | tee logs/dev.log
