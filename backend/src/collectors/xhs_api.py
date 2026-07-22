"""
小红书数据采集器

职责：
- 调用 TikHubClient 拉数据
- 归一化字段写入 MongoDB（upsert，按 note_id / comment_id 去重）
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pymongo import UpdateOne

from src.collectors.tikhub import TikHubError, tikhub_client
from src.config import settings
from src.db.mongodb import mongodb

logger = logging.getLogger(__name__)


def note_matches_keyword(note: Dict[str, Any], keyword: str) -> bool:
    """标题/正文/标签是否真正包含关键词（过滤搜索的模糊/同音匹配噪声）。

    采集入库过滤与存量清理脚本共用此规则，保证口径一致。
    """
    blob = (
        f"{note.get('title', '')} {note.get('content', '')} "
        f"{' '.join(note.get('tags') or [])}"
    ).lower()
    return keyword.lower() in blob


def _published_after(note: Dict[str, Any], cutoff: datetime) -> bool:
    """发布时间晚于 cutoff（缺失发布时间的保留，不误杀）"""
    pub = note.get("published_at")
    if not isinstance(pub, datetime):
        return True
    return pub >= cutoff


def note_dedup_key(note: Dict[str, Any]) -> str:
    """规范化去重键：同一篇笔记的变体 note_id 共享 (作者 + 发布时间)。

    上游会给同一篇笔记返回中段不同的变体 note_id（如 ...0000... / ...0002...），
    按 note_id 去重会漏。作者 user_id + 发布时间秒级一致，是稳定的"同篇"身份；
    缺任一信息则回退到 note_id 本身，避免把未知项错并。
    """
    author = note.get("author") or {}
    uid = author.get("user_id") or ""
    pub = note.get("published_at")
    if uid and pub is not None:
        pub_s = pub.isoformat() if hasattr(pub, "isoformat") else str(pub)
        return f"{uid}|{pub_s}"
    return f"nid:{note.get('note_id', '')}"


class DataCollector:
    """数据采集器 + 持久化"""

    def __init__(self) -> None:
        self.client = tikhub_client

    # ============ 采集 ============
    async def collect_and_upsert_by_keyword(
        self, keyword: str, category: str = "brand", max_notes: Optional[int] = None
    ) -> List[str]:
        """按关键词搜索并入库，返回新增的 note_id 列表。

        按"排序 × 页数"计划抓取：时间流为主（``SEARCH_PAGES_BY_CATEGORY``），
        general 排序补采样（``SEARCH_GENERAL_PAGES_BY_CATEGORY``）——两个结果集
        互补，时间流会漏排序靠后的真实用户帖。跨页/跨排序/跨轮重复由
        ``upsert_notes`` 按 ``dedup_key`` 去重，只刷新不重复入库。
        """
        time_pages = settings.SEARCH_PAGES_BY_CATEGORY.get(category, 1)
        general_pages = settings.SEARCH_GENERAL_PAGES_BY_CATEGORY.get(category, 0)
        plan = [(settings.SEARCH_SORT_TYPE, time_pages), ("general", general_pages)]
        limit = max_notes or sum(p for _, p in plan) * settings.MAX_NOTES_PER_PAGE

        notes: List[Dict[str, Any]] = []
        for sort_type, pages in plan:
            for page in range(1, pages + 1):
                try:
                    batch = await self.client.search_notes(
                        keyword, page=page, sort_type=sort_type
                    )
                except TikHubError as e:
                    logger.error(
                        "关键词 %s %s 第 %d 页搜索失败: %s", keyword, sort_type, page, e
                    )
                    break
                if not batch:
                    break  # 该排序没有更多结果，换下一个排序
                notes.extend(batch)

        notes = [n for n in notes if n.get("note_id")]

        # 相关性过滤：小红书搜索是模糊/同音匹配，time_descending 会捞进大量沾边噪声
        # （如"澜大"匹配到"兰大"）。只留标题/正文/标签里真正出现关键词的笔记。
        if settings.SEARCH_REQUIRE_KEYWORD_MATCH:
            kept = [n for n in notes if note_matches_keyword(n, keyword)]
            dropped = len(notes) - len(kept)
            if dropped:
                logger.info("关键词 %s 过滤无关笔记 %d 条", keyword, dropped)
            notes = kept

        # 兜底：接口偶尔混排老帖，丢掉发布超过 N 天的（防"一年前的帖子"）
        if settings.SEARCH_MAX_AGE_DAYS > 0:
            cutoff = datetime.utcnow() - timedelta(days=settings.SEARCH_MAX_AGE_DAYS)
            fresh = [n for n in notes if _published_after(n, cutoff)]
            stale = len(notes) - len(fresh)
            if stale:
                logger.info("关键词 %s 过滤超龄老帖 %d 条", keyword, stale)
            notes = fresh

        notes = notes[:limit]
        for n in notes:
            n["category"] = category  # brand / competitor / industry

        return await self.upsert_notes(notes)

    async def collect_note_comments(
        self, note_id: str, max_comments: Optional[int] = None
    ) -> int:
        """拉单条笔记的评论并入库，返回入库条数"""
        limit = max_comments or settings.MAX_COMMENTS_PER_NOTE
        collected: List[Dict[str, Any]] = []
        cursor = ""

        while len(collected) < limit:
            try:
                batch, cursor = await self.client.get_note_comments(note_id, cursor)
            except TikHubError as e:
                logger.warning("获取评论失败 note_id=%s: %s", note_id, e)
                break
            if not batch:
                break
            collected.extend(batch)
            if not cursor:
                break

        collected = collected[:limit]
        await self.upsert_comments(collected)
        await self._mark_comments_collected(note_id)
        return len(collected)

    # ============ 持久化 ============
    async def upsert_notes(self, notes: List[Dict[str, Any]]) -> List[str]:
        """批量 upsert 笔记；按 canonical key 去重，返回首次入库的 note_id 列表"""
        if not notes:
            return []

        collection = mongodb.get_collection("notes")
        now = datetime.utcnow()

        # 批内先按 canonical key 去重（同批的变体只留首个）
        seen: set[str] = set()
        deduped: List[Dict[str, Any]] = []
        for n in notes:
            key = note_dedup_key(n)
            n["dedup_key"] = key
            if key not in seen:
                seen.add(key)
                deduped.append(n)

        # 查库中已存在的 dedup_key，用于区分"新笔记"
        existing: set[str] = set()
        async for doc in collection.find(
            {"dedup_key": {"$in": list(seen)}}, {"dedup_key": 1}
        ):
            existing.add(doc["dedup_key"])

        new_ids: List[str] = []
        ops: List[UpdateOne] = []
        for note in deduped:
            key = note["dedup_key"]
            if key not in existing:
                new_ids.append(note["note_id"])
            # note_id 用首个变体固定，其余字段随最新刷新
            set_fields = {k: v for k, v in note.items() if k != "note_id"}
            set_fields["updated_at"] = now
            ops.append(
                UpdateOne(
                    {"dedup_key": key},
                    {
                        "$set": set_fields,
                        "$setOnInsert": {
                            "note_id": note["note_id"],
                            "collected_at": now,
                        },
                    },
                    upsert=True,
                )
            )

        if ops:
            await collection.bulk_write(ops, ordered=False)
            logger.info("笔记入库: 去重后 %d 条，新增 %d", len(ops), len(new_ids))

        return new_ids

    async def upsert_comments(self, comments: List[Dict[str, Any]]) -> None:
        """批量 upsert 评论（包含子评论，递归拍平）"""
        flat = self._flatten_comments(comments)
        if not flat:
            return

        collection = mongodb.get_collection("comments")
        now = datetime.utcnow()
        ops = [
            UpdateOne(
                {"comment_id": c["comment_id"]},
                {"$set": {**c, "updated_at": now}, "$setOnInsert": {"collected_at": now}},
                upsert=True,
            )
            for c in flat
            if c.get("comment_id")
        ]
        if ops:
            await collection.bulk_write(ops, ordered=False)
            logger.info("评论入库: %d 条", len(ops))

    async def _mark_comments_collected(self, note_id: str) -> None:
        await mongodb.get_collection("notes").update_one(
            {"note_id": note_id},
            {"$set": {"comments_collected_at": datetime.utcnow()}},
        )

    @staticmethod
    def _flatten_comments(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """把嵌套的 replies 拍平存储，避免 MongoDB 嵌套过深"""
        result: List[Dict[str, Any]] = []
        for c in comments:
            replies = c.get("replies") or []
            result.append({**c, "replies": [r["comment_id"] for r in replies if r.get("comment_id")]})
            result.extend(DataCollector._flatten_comments(replies))
        return result


# ============ 调试入口 ============
async def _smoke_test(keyword: str = "口红") -> None:
    """本地调试：import asyncio; asyncio.run(_smoke_test())"""
    from src.db.mongodb import init_mongodb, close_mongodb

    logging.basicConfig(level=logging.INFO)
    await init_mongodb()
    try:
        collector = DataCollector()
        new_ids = await collector.collect_and_upsert_by_keyword(keyword, category="brand")
        print(f"新增 {len(new_ids)} 条笔记: {new_ids[:3]}")
        if new_ids:
            n = await collector.collect_note_comments(new_ids[0])
            print(f"第一条笔记抓到 {n} 条评论")
    finally:
        await close_mongodb()
        await tikhub_client.aclose()


if __name__ == "__main__":
    import sys

    kw = sys.argv[1] if len(sys.argv) > 1 else "口红"
    asyncio.run(_smoke_test(kw))
