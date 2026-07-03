"""
竞品监控服务

数据模型说明：
- 笔记的 ``category`` 只存桶值（brand/competitor/industry），不是竞品名。
- 真正的竞品名存在 ``search_keyword`` 字段（搜索时用的关键词）。
- 因此所有竞品查询都以 ``search_keyword`` 为键，时间轴用 ``published_at``
  （笔记发布时间，反映真实舆情），而非 ``collected_at``（抓取时间）。
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.config import settings
from src.db.mongodb import mongodb
from src.models.note import CompetitorData

# 复用的情感聚合表达式：一次扫描算出正/负计数与均分
_SENTIMENT_FACET = {
    "note_count": {"$sum": 1},
    "positive": {
        "$sum": {"$cond": [{"$eq": ["$sentiment.label", "positive"]}, 1, 0]}
    },
    "negative": {
        "$sum": {"$cond": [{"$eq": ["$sentiment.label", "negative"]}, 1, 0]}
    },
    "avg_score": {"$avg": {"$ifNull": ["$sentiment.score", 0.5]}},
    "total_mentions": {"$sum": {"$ifNull": ["$stats.comments", 0]}},
}


class CompetitorMonitor:
    """竞品监控器"""

    async def analyze_competitor(self, name: str, days: int = 30) -> CompetitorData:
        """聚合单个竞品（按 search_keyword）在 days 天内的舆情指标"""
        start_time = datetime.utcnow() - timedelta(days=days)

        cursor = mongodb.get_collection("notes").aggregate(
            [
                {"$match": {"search_keyword": name,
                            "published_at": {"$gte": start_time}}},
                {"$group": {"_id": None, **_SENTIMENT_FACET}},
            ]
        )
        rows = await cursor.to_list(length=1)
        if not rows:
            return CompetitorData(
                name=name,
                note_count=0,
                avg_sentiment_score=0.5,
                positive_rate=0.0,
                negative_rate=0.0,
                total_mentions=0,
            )

        row = rows[0]
        count = row["note_count"]
        return CompetitorData(
            name=name,
            note_count=count,
            avg_sentiment_score=row["avg_score"],
            positive_rate=row["positive"] / count,
            negative_rate=row["negative"] / count,
            total_mentions=row["total_mentions"],
        )

    async def compare_competitors(
        self, names: Optional[List[str]] = None, days: int = 30
    ) -> List[CompetitorData]:
        """比较多个竞品；names 为空时取配置里的竞品关键词"""
        names = names or settings.MONITOR_KEYWORDS_COMPETITOR
        results = [await self.analyze_competitor(n, days) for n in names]
        return sorted(results, key=lambda x: x.note_count, reverse=True)

    async def get_competitor_trends(
        self, name: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """单个竞品的逐日趋势（一次聚合 + 补齐空白日，无 N+1）"""
        start_time = (datetime.utcnow() - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        cursor = mongodb.get_collection("notes").aggregate(
            [
                {"$match": {"search_keyword": name,
                            "published_at": {"$gte": start_time}}},
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y-%m-%d", "date": "$published_at"
                            }
                        },
                        "note_count": {"$sum": 1},
                        "positive_count": {
                            "$sum": {"$cond": [
                                {"$eq": ["$sentiment.label", "positive"]}, 1, 0]}
                        },
                        "negative_count": {
                            "$sum": {"$cond": [
                                {"$eq": ["$sentiment.label", "negative"]}, 1, 0]}
                        },
                    }
                },
            ]
        )
        by_day = {r["_id"]: r async for r in cursor}

        # 补齐 days 个连续日期，缺失日补零
        out: List[Dict[str, Any]] = []
        for i in range(days):
            day = start_time + timedelta(days=i)
            key = day.strftime("%Y-%m-%d")
            row = by_day.get(key)
            out.append(
                {
                    "date": day,
                    "note_count": row["note_count"] if row else 0,
                    "positive_count": row["positive_count"] if row else 0,
                    "negative_count": row["negative_count"] if row else 0,
                }
            )
        return out


competitor_monitor = CompetitorMonitor()
