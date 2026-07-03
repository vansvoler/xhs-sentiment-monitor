"""
趋势分析服务

设计要点：
- 时间轴统一用 ``published_at``（笔记发布时间），反映真实舆情热度曲线，
  而非 ``collected_at``（我方抓取时间，只代表爬虫排班）。
- 逐日序列用单条聚合管道按天分桶，杜绝"循环 N 天 × 全表加载"的 N+1。
- 热词数据源是 ``search_keyword``（命中该笔记的监控词，始终有值）；
  笔记的 ``tags`` 在搜索接口下恒为空，不可用。
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.db.mongodb import mongodb
from src.models.note import TrendData

# 按天分桶的情感计数表达式
_DAILY_SENTIMENT = {
    "total_notes": {"$sum": 1},
    "positive_count": {
        "$sum": {"$cond": [{"$eq": ["$sentiment.label", "positive"]}, 1, 0]}
    },
    "negative_count": {
        "$sum": {"$cond": [{"$eq": ["$sentiment.label", "negative"]}, 1, 0]}
    },
    "neutral_count": {
        "$sum": {"$cond": [{"$eq": ["$sentiment.label", "neutral"]}, 1, 0]}
    },
    "score_sum": {"$sum": {"$ifNull": ["$sentiment.score", 0.5]}},
}

_DAY_FMT = "%Y-%m-%d"


def _day_str(field: str) -> Dict[str, Any]:
    """field 是 Mongo 字段引用（如 "$published_at"）"""
    return {"$dateToString": {"format": _DAY_FMT, "date": field}}


class TrendAnalyzer:
    """趋势分析器"""

    async def get_trend_series(
        self, days: int = 7, category: Optional[str] = None
    ) -> List[TrendData]:
        """逐日趋势序列：3 条聚合（笔记/评论/热词）拼装，与 days 无关"""
        start = (datetime.utcnow() - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        notes_by_day = await self._notes_by_day(start, category)
        comments_by_day = await self._comments_by_day(start)
        keywords_by_day = await self._top_keywords_by_day(start, category=category)

        out: List[TrendData] = []
        for i in range(days):
            day = start + timedelta(days=i)
            key = day.strftime(_DAY_FMT)
            n = notes_by_day.get(key) or {}
            total = n.get("total_notes", 0)
            out.append(
                TrendData(
                    timestamp=day,
                    positive_count=n.get("positive_count", 0),
                    negative_count=n.get("negative_count", 0),
                    neutral_count=n.get("neutral_count", 0),
                    total_notes=total,
                    total_comments=comments_by_day.get(key, 0),
                    avg_sentiment_score=(n["score_sum"] / total) if total else 0.5,
                    hot_keywords=keywords_by_day.get(key, []),
                )
            )
        return out

    async def analyze_daily_trend(
        self, date: Optional[datetime] = None
    ) -> TrendData:
        """单日趋势（默认今天）"""
        day = (date or datetime.utcnow()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return await self._single_day(day)

    async def get_hot_topics(
        self, limit: int = 10, hours: int = 24, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """近 hours 小时内、按互动量排序的热门笔记"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        match: Dict[str, Any] = {"published_at": {"$gte": start_time}}
        if category:
            match["category"] = category
        cursor = (
            mongodb.get_collection("notes")
            .find(match)
            .sort([("stats.likes", -1), ("stats.comments", -1)])
        )
        notes = await cursor.to_list(length=limit)
        return [
            {
                "note_id": n.get("note_id"),
                "title": n.get("title"),
                "tags": n.get("tags", []),
                "likes": n.get("stats", {}).get("likes", 0),
                "comments": n.get("stats", {}).get("comments", 0),
                "sentiment": n.get("sentiment"),
            }
            for n in notes
        ]

    # ---------------- 内部聚合 ----------------
    async def _notes_by_day(
        self, start: datetime, category: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        match: Dict[str, Any] = {"published_at": {"$gte": start}}
        if category:
            match["category"] = category
        cursor = mongodb.get_collection("notes").aggregate(
            [
                {"$match": match},
                {"$group": {"_id": _day_str("$published_at"), **_DAILY_SENTIMENT}},
            ]
        )
        return {r["_id"]: r async for r in cursor}

    async def _comments_by_day(self, start: datetime) -> Dict[str, int]:
        cursor = mongodb.get_collection("comments").aggregate(
            [
                {"$match": {"created_at": {"$gte": start}}},
                {"$group": {"_id": _day_str("$created_at"), "n": {"$sum": 1}}},
            ]
        )
        return {r["_id"]: r["n"] async for r in cursor}

    async def _top_keywords_by_day(
        self, start: datetime, top: int = 5, category: Optional[str] = None
    ) -> Dict[str, List[str]]:
        match: Dict[str, Any] = {"published_at": {"$gte": start},
                                 "search_keyword": {"$ne": None}}
        if category:
            match["category"] = category
        cursor = mongodb.get_collection("notes").aggregate(
            [
                {"$match": match},
                {
                    "$group": {
                        "_id": {"day": _day_str("$published_at"),
                                "kw": "$search_keyword"},
                        "n": {"$sum": 1},
                    }
                },
                {"$sort": {"n": -1}},
            ]
        )
        buckets: Dict[str, List[str]] = defaultdict(list)
        async for r in cursor:
            day = r["_id"]["day"]
            if len(buckets[day]) < top:
                buckets[day].append(r["_id"]["kw"])
        return buckets

    async def _single_day(self, day: datetime) -> TrendData:
        """指定历史单日（analyze_daily_trend 走非今天分支时用）"""
        nxt = day + timedelta(days=1)
        match = {"published_at": {"$gte": day, "$lt": nxt}}
        notes = mongodb.get_collection("notes")
        rows = await notes.aggregate(
            [{"$match": match}, {"$group": {"_id": None, **_DAILY_SENTIMENT}}]
        ).to_list(length=1)
        comments = await mongodb.get_collection("comments").count_documents(
            {"created_at": {"$gte": day, "$lt": nxt}}
        )
        kw_cursor = notes.aggregate(
            [
                {"$match": {**match, "search_keyword": {"$ne": None}}},
                {"$group": {"_id": "$search_keyword", "n": {"$sum": 1}}},
                {"$sort": {"n": -1}},
                {"$limit": 5},
            ]
        )
        hot = [r["_id"] async for r in kw_cursor]
        if not rows:
            return TrendData(timestamp=day, positive_count=0, negative_count=0,
                             neutral_count=0, total_notes=0, total_comments=comments,
                             avg_sentiment_score=0.5, hot_keywords=hot)
        r = rows[0]
        total = r["total_notes"]
        return TrendData(
            timestamp=day,
            positive_count=r["positive_count"],
            negative_count=r["negative_count"],
            neutral_count=r["neutral_count"],
            total_notes=total,
            total_comments=comments,
            avg_sentiment_score=(r["score_sum"] / total) if total else 0.5,
            hot_keywords=hot,
        )


trend_analyzer = TrendAnalyzer()
