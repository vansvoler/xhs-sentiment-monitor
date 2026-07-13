"""
孤儿词笔记清理（一次性运维）

监控词在界面上删除后（``keyword_config.remove``），旧笔记的 ``search_keyword``
仍指向已停用的词（如早期简称"学通"、测试词"猫粮"），继续污染统计与工作台。
本脚本删除 ``search_keyword`` 不在当前 ``monitor_keywords`` 里的笔记及其评论、告警。

注意：孤儿词里可能混有真正相关的历史笔记（如"学通"简称下确有渊学通内容），
但该主体现已由更精准的全称词（"渊学通"）持续监控，故整体清除利大于弊。

一刀切清所有孤儿词往往过猛（`犀牛` 这类退役竞品词攒着几百篇有价值的历史），
故支持 ``--keyword`` 定向只清指定的词，可重复传。

安全：**默认 dry-run 只统计不删除**，确认后加 ``--apply`` 才真正删。
用法：``bash backend/scripts/purge_orphan_keywords.sh [--keyword yxt] [--apply]``
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from src.db.mongodb import close_mongodb, init_mongodb, mongodb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def collect_orphans(
    only: Optional[Sequence[str]] = None,
) -> tuple[List[Any], List[str], Counter]:
    """返回 (待删 _id, 待删 note_id, 按孤儿词统计)。

    仅清 ``search_keyword`` 有值但不在监控词里的笔记；null/空的不动
    （无从判定归属，交由 relevance 过滤处理）。``only`` 非空时进一步限定到这些词。
    """
    active = set(await mongodb.get_collection("monitor_keywords").distinct("keyword"))
    targets = set(only or ())
    doc_ids: List[Any] = []
    note_ids: List[str] = []
    by_keyword: Counter = Counter()

    async for n in mongodb.get_collection("notes").find(
        {"search_keyword": {"$nin": [None, ""]}},
        {"search_keyword": 1, "note_id": 1},
    ):
        kw = n["search_keyword"]
        if kw in active or (targets and kw not in targets):
            continue
        doc_ids.append(n["_id"])
        if n.get("note_id"):
            note_ids.append(n["note_id"])
        by_keyword[kw] += 1

    return doc_ids, note_ids, by_keyword


async def run(apply: bool, only: Optional[Sequence[str]] = None) -> Dict[str, int]:
    await init_mongodb()

    if only:
        active = set(
            await mongodb.get_collection("monitor_keywords").distinct("keyword")
        )
        if still_active := [k for k in only if k in active]:
            await close_mongodb()
            raise SystemExit(
                f"拒绝执行：{'、'.join(still_active)} 仍在监控词表里，不是孤儿词。"
                f"请先在前端或 DELETE /api/config/keywords/<kw> 删除该词。"
            )
        logger.info("定向清理，只处理：%s", "、".join(only))
    doc_ids, note_ids, by_keyword = await collect_orphans(only)
    logger.info("孤儿词笔记：%d 条", len(doc_ids))
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
    return {"orphan": len(doc_ids), "deleted": deleted}


def main() -> None:
    ap = argparse.ArgumentParser(description="孤儿词笔记清理")
    ap.add_argument("--apply", action="store_true", help="真正删除（默认 dry-run）")
    ap.add_argument(
        "--keyword", action="append", metavar="KW",
        help="只清这个孤儿词，可重复传；不传则清全部孤儿词",
    )
    args = ap.parse_args()
    asyncio.run(run(args.apply, args.keyword))


if __name__ == "__main__":
    main()
