#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python - <<'PY'
import asyncio
from pathlib import Path

from src.db.mongodb import close_mongodb, init_mongodb
from src.services.intel_seed import seed_intel_items


async def main() -> None:
    await init_mongodb()
    count = await seed_intel_items(Path("temp/intel_seed.json"))
    print(f"seeded={count}")
    await close_mongodb()


asyncio.run(main())
PY
