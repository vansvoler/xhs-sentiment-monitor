"""
存量偏题笔记清理（一次性运维）

入库过滤（``SEARCH_REQUIRE_KEYWORD_MATCH``）上线前，搜索的模糊/同音匹配
捞进了大量与关键词无关的笔记。本脚本按同一规则回扫存量：
标题/正文/标签均不含 ``search_keyword`` 的笔记视为噪声，连带删除其评论与告警。

安全：**默认 dry-run 只统计不删除**，确认后加 ``--apply`` 才真正删。
用法：``bash backend/scripts/purge_offtopic.sh [--apply]``
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from collections import Counter
from typing import Any, Dict, List

from src.collectors.xhs_api import note_matches_keyword
from src.db.mongodb import close_mongodb, init_mongodb, mongodb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def collect_offtopic() -> tuple[List[Any], List[str], Counter]:
    """扫描全库，返回 (待删 _id 列表, 待删 note_id 列表, 按关键词统计)"""
    coll = mongodb.get_collection("notes")
    doc_ids: List[Any] = []
    note_ids: List[str] = []
    by_keyword: Counter = Counter()

    async for n in coll.find(
        {"search_keyword": {"$nin": [None, ""]}},
        {"title": 1, "content": 1, "tags": 1, "search_keyword": 1, "note_id": 1},
    ):
        if note_matches_keyword(n, n["search_keyword"]):
            continue
        doc_ids.append(n["_id"])
        if n.get("note_id"):
            note_ids.append(n["note_id"])
        by_keyword[n["search_keyword"]] += 1

    return doc_ids, note_ids, by_keyword


async def run(apply: bool) -> Dict[str, int]:
    await init_mongodb()

    doc_ids, note_ids, by_keyword = await collect_offtopic()
    logger.info("偏题笔记：%d 条", len(doc_ids))
    for kw, n in by_keyword.most_common():
        logger.info("  %-12s %d 条", kw, n)

    comments = mongodb.get_collection("comments")
    alerts = mongodb.get_collection("alerts")
    n_comments = await comments.count_documents({"note_id": {"$in": note_ids}})
    n_alerts = await alerts.count_documents({"note_id": {"$in": note_ids}})
    logger.info("关联评论：%d 条，关联告警：%d 条", n_comments, n_alerts)

    deleted = 0
    if apply and doc_ids:
        res = await mongodb.get_collection("notes").delete_many(
            {"_id": {"$in": doc_ids}}
        )
        deleted = res.deleted_count
        await comments.delete_many({"note_id": {"$in": note_ids}})
        await alerts.delete_many({"note_id": {"$in": note_ids}})
        logger.info(
            "已删除：笔记 %d / 评论 %d / 告警 %d", deleted, n_comments, n_alerts
        )
    elif not apply:
        logger.info("dry-run（未删除）。确认后加 --apply 执行。")

    await close_mongodb()
    return {
        "offtopic": len(doc_ids),
        "comments": n_comments,
        "alerts": n_alerts,
        "deleted": deleted,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="存量偏题笔记清理")
    ap.add_argument("--apply", action="store_true", help="真正删除（默认 dry-run）")
    args = ap.parse_args()
    asyncio.run(run(args.apply))


if __name__ == "__main__":
    main()
