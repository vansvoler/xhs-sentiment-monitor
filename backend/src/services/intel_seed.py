"""
运营情报 seed / fixture 读取与导入
"""
import json
from pathlib import Path

from src.db.mongodb import mongodb
from src.models.intel import IntelItem


def load_seed_items(seed_path: Path) -> list[IntelItem]:
    """从 JSON fixture 读取统一情报项"""

    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    return [IntelItem(**item) for item in payload]


async def seed_intel_items(seed_path: Path) -> int:
    """把 seed 数据 upsert 到 intel_items 集合"""

    items = load_seed_items(seed_path)
    collection = mongodb.get_collection("intel_items")

    for item in items:
        await collection.update_one(
            {"item_id": item.item_id},
            {"$set": item.model_dump(mode="json")},
            upsert=True,
        )

    return len(items)
