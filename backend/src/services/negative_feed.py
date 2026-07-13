"""
负面舆情工作台服务

把笔记与评论两类负面内容统一成同构条目（``NegativeItem``），支撑处置流：
- 笔记：直接查 ``notes``（排除语义偏题）。
- 评论：``$lookup`` 关联父笔记取标题/监控词/分类，父笔记偏题的一并排除。
- 处置状态写回原文档 ``handle_status``（open/handled），字段缺失视为 open。

影响力排序：笔记按作者粉丝数，评论按点赞数——负面内容传播风险的最简代理指标。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.db.filters import ON_TOPIC
from src.db.mongodb import mongodb
from src.models.sentiment import NegativeItem

_EXCERPT_LEN = 120

# kind → (排序字段: influence / latest)
_SORTS: Dict[str, Dict[str, List[tuple]]] = {
    "note": {
        "influence": [("author.fans_count", -1), ("sentiment.score", -1)],
        "latest": [("published_at", -1)],
    },
    "comment": {
        "influence": [("likes", -1), ("sentiment.score", -1)],
        "latest": [("created_at", -1)],
    },
}


def note_url(note_id: str, xsec_token: Optional[str] = None) -> str:
    """小红书原文链接；带 xsec_token 时可直接在 PC 端打开"""
    url = f"https://www.xiaohongshu.com/explore/{note_id}"
    if xsec_token:
        url += f"?xsec_token={xsec_token}&xsec_source=pc_search"
    return url


def _status_query(status: str) -> Dict[str, Any]:
    if status == "handled":
        return {"handle_status": "handled"}
    if status == "open":
        return {"handle_status": {"$ne": "handled"}}
    return {}  # all


def _note_item(doc: Dict[str, Any]) -> NegativeItem:
    return NegativeItem(
        kind="note",
        id=doc["note_id"],
        note_id=doc["note_id"],
        title=doc.get("title") or "(无标题)",
        excerpt=(doc.get("content") or "")[:_EXCERPT_LEN],
        author=doc.get("author") or {},
        sentiment=doc["sentiment"],
        keyword=doc.get("search_keyword"),
        category=doc.get("category"),
        happened_at=doc["published_at"],
        likes=(doc.get("stats") or {}).get("likes", 0),
        url=note_url(doc["note_id"], doc.get("xsec_token")),
        handle_status=doc.get("handle_status") or "open",
    )


def _comment_item(doc: Dict[str, Any]) -> NegativeItem:
    note = doc["note"]
    return NegativeItem(
        kind="comment",
        id=doc["comment_id"],
        note_id=doc["note_id"],
        title=note.get("title") or "(无标题)",
        excerpt=(doc.get("content") or "")[:_EXCERPT_LEN],
        author=doc.get("author") or {},
        sentiment=doc["sentiment"],
        keyword=note.get("search_keyword"),
        category=note.get("category"),
        happened_at=doc["created_at"],
        likes=doc.get("likes", 0),
        url=note_url(doc["note_id"], note.get("xsec_token")),
        handle_status=doc.get("handle_status") or "open",
    )


class NegativeFeed:
    """负面内容统一查询 + 处置状态"""

    async def list_items(  # noqa: PLR0913
        self,
        kind: str = "note",
        *,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        status: str = "open",
        sort: str = "influence",
    ) -> List[NegativeItem]:
        sort_spec = _SORTS[kind].get(sort) or _SORTS[kind]["influence"]
        if kind == "note":
            return await self._list_notes(
                skip, limit, category, keyword, status, sort_spec
            )
        return await self._list_comments(
            skip, limit, category, keyword, status, sort_spec
        )

    async def _list_notes(  # noqa: PLR0913
        self, skip, limit, category, keyword, status, sort_spec
    ) -> List[NegativeItem]:
        query: Dict[str, Any] = {
            **ON_TOPIC,
            "sentiment.label": "negative",
            **_status_query(status),
        }
        if category:
            query["category"] = category
        if keyword:
            query["search_keyword"] = keyword
        cursor = (
            mongodb.get_collection("notes")
            .find(query).sort(sort_spec).skip(skip).limit(limit)
        )
        return [_note_item(d) async for d in cursor]

    async def _list_comments(  # noqa: PLR0913
        self, skip, limit, category, keyword, status, sort_spec
    ) -> List[NegativeItem]:
        note_match: Dict[str, Any] = {"note.relevance": {"$ne": "off_topic"}}
        if category:
            note_match["note.category"] = category
        if keyword:
            note_match["note.search_keyword"] = keyword

        pipeline = [
            {"$match": {"sentiment.label": "negative", **_status_query(status)}},
            {"$lookup": {"from": "notes", "localField": "note_id",
                         "foreignField": "note_id", "as": "note"}},
            {"$unwind": "$note"},
            {"$match": note_match},
            {"$sort": dict(sort_spec)},
            {"$skip": skip},
            {"$limit": limit},
        ]
        cursor = mongodb.get_collection("comments").aggregate(pipeline)
        return [_comment_item(d) async for d in cursor]

    async def set_status(self, kind: str, item_id: str, status: str) -> bool:
        """标记处置状态，返回是否命中文档"""
        coll_name = "notes" if kind == "note" else "comments"
        id_field = "note_id" if kind == "note" else "comment_id"
        res = await mongodb.get_collection(coll_name).update_one(
            {id_field: item_id}, {"$set": {"handle_status": status}}
        )
        return res.matched_count > 0

    async def summary(self) -> Dict[str, int]:
        """未处置的负面笔记/评论数（工作台徽标用）"""
        open_q = _status_query("open")
        notes_open = await mongodb.get_collection("notes").count_documents(
            {**ON_TOPIC, "sentiment.label": "negative", **open_q}
        )
        rows = await mongodb.get_collection("comments").aggregate([
            {"$match": {"sentiment.label": "negative", **open_q}},
            {"$lookup": {"from": "notes", "localField": "note_id",
                         "foreignField": "note_id", "as": "note"}},
            {"$unwind": "$note"},
            {"$match": {"note.relevance": {"$ne": "off_topic"}}},
            {"$count": "n"},
        ]).to_list(length=1)
        comments_open = rows[0]["n"] if rows else 0
        return {"notes_open": notes_open, "comments_open": comments_open}


negative_feed = NegativeFeed()
