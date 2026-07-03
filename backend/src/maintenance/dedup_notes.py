"""
笔记去重清理（一次性运维）

同一篇笔记会被上游返回多个变体 note_id 而重复入库。本脚本按 canonical key
``(作者 user_id + 发布时间)`` 合并：每组保留互动量（赞）最高的一条，其余删除。

安全：**默认 dry-run 只统计不删除**，确认后加 ``--apply`` 才真正删。
用法：``bash backend/scripts/dedup_notes.sh [--apply]``
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any, Dict, List

from src.collectors.xhs_api import note_dedup_key
from src.db.mongodb import close_mongodb, init_mongodb, mongodb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_keys(coll) -> int:
    """给缺 dedup_key 的历史文档补键"""
    filled = 0
    async for d in coll.find(
        {"dedup_key": {"$exists": False}},
        {"author": 1, "published_at": 1, "note_id": 1},
    ):
        await coll.update_one(
            {"_id": d["_id"]}, {"$set": {"dedup_key": note_dedup_key(d)}}
        )
        filled += 1
    return filled


async def collect_redundant(coll) -> List[Any]:
    """返回待删除的冗余文档 _id（每组保留赞数最高的一条）"""
    to_delete: List[Any] = []
    async for g in coll.aggregate(
        [
            {
                "$group": {
                    "_id": "$dedup_key",
                    "n": {"$sum": 1},
                    "docs": {
                        "$push": {
                            "id": "$_id",
                            "likes": {"$ifNull": ["$stats.likes", 0]},
                        }
                    },
                }
            },
            {"$match": {"n": {"$gt": 1}}},
        ]
    ):
        ranked = sorted(g["docs"], key=lambda d: d["likes"], reverse=True)
        to_delete.extend(d["id"] for d in ranked[1:])  # 保留首个（赞最高）
    return to_delete


async def run(apply: bool) -> Dict[str, int]:
    await init_mongodb()
    coll = mongodb.get_collection("notes")

    filled = await backfill_keys(coll)
    logger.info("补齐 dedup_key：%d 条", filled)

    to_delete = await collect_redundant(coll)
    logger.info("冗余待删：%d 条", len(to_delete))

    deleted = 0
    if apply and to_delete:
        res = await coll.delete_many({"_id": {"$in": to_delete}})
        deleted = res.deleted_count
        logger.info("已删除：%d 条", deleted)
    elif not apply:
        logger.info("dry-run（未删除）。确认后加 --apply 执行。")

    await close_mongodb()
    return {"backfilled": filled, "redundant": len(to_delete), "deleted": deleted}


def main() -> None:
    ap = argparse.ArgumentParser(description="笔记去重清理")
    ap.add_argument("--apply", action="store_true", help="真正删除（默认 dry-run）")
    args = ap.parse_args()
    asyncio.run(run(args.apply))


if __name__ == "__main__":
    main()
