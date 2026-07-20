"""
竞品监控服务

数据模型说明：
- 笔记的 ``category`` 只存桶值（brand/competitor/industry），不是竞品名。
- 真正的竞品名存在 ``search_keyword`` 字段（搜索时用的关键词）。
- 因此所有竞品查询都以 ``search_keyword`` 为键，时间轴用 ``published_at``
  （笔记发布时间，反映真实舆情），而非 ``collected_at``（抓取时间）。
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.config import settings
from src.db.filters import ON_TOPIC
from src.db.mongodb import mongodb
from src.models.note import CompetitorData
from src.services.keyword_config import keyword_config

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

    async def analyze_competitor(
        self,
        name: str,
        days: int = 30,
        keywords: Optional[List[str]] = None,
        is_own: bool = False,
    ) -> CompetitorData:
        """聚合关键词组在 days 天内的舆情指标。

        默认单词（name 即 search_keyword）；本品牌可传多个品牌词聚成一组
        （如 渊学通 + yxt 是同一主体的两个搜索词）。情绪统计全部相关笔记
        （不再按昵称剔除"自家号"：新机构大量养 KOC 素人号，昵称无品牌名，
        按昵称过滤挡不住、反而给出假的准确感）。
        """
        kws = keywords or [name]
        start_time = datetime.utcnow() - timedelta(days=days)

        cursor = mongodb.get_collection("notes").aggregate(
            [
                {"$match": {**ON_TOPIC, "search_keyword": {"$in": kws},
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
                positive_count=0,
                negative_count=0,
                total_mentions=0,
                is_own=is_own,
            )

        row = rows[0]
        count = row["note_count"]
        return CompetitorData(
            name=name,
            note_count=count,
            avg_sentiment_score=row["avg_score"],
            positive_count=row["positive"],
            negative_count=row["negative"],
            total_mentions=row["total_mentions"],
            is_own=is_own,
        )

    async def compare_competitors(
        self, names: Optional[List[str]] = None, days: int = 30
    ) -> List[CompetitorData]:
        """本品牌 + 竞品同场对比；names 为空时取运行时监控词。

        本品牌是全部品牌词的聚合（一根柱），置于首位；竞品按声量降序。
        显式传 names 时保持旧行为（只比给定的词）。
        """
        results: List[CompetitorData] = []
        if not names:
            grouped = await keyword_config.list_grouped()
            if grouped["brand"]:
                results.append(await self.analyze_competitor(
                    "本品牌", days, keywords=grouped["brand"], is_own=True,
                ))
            names = grouped["competitor"] or settings.MONITOR_KEYWORDS_COMPETITOR
        competitors = [await self.analyze_competitor(n, days) for n in names]
        competitors.sort(key=lambda x: x.note_count, reverse=True)
        return results + competitors

    async def get_competitor_trends(
        self, name: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """单个竞品的逐日趋势（一次聚合 + 补齐空白日，无 N+1）；日界按北京时间"""
        cst = timezone(timedelta(hours=8))
        start_local = datetime.now(cst).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=days - 1)
        start_time = start_local.astimezone(timezone.utc).replace(tzinfo=None)

        cursor = mongodb.get_collection("notes").aggregate(
            [
                {"$match": {**ON_TOPIC, "search_keyword": name,
                            "published_at": {"$gte": start_time}}},
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y-%m-%d", "date": "$published_at",
                                "timezone": "+08:00",
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

        # 补齐 days 个连续日期，缺失日补零（标签用本地日期）
        out: List[Dict[str, Any]] = []
        for i in range(days):
            day = start_local + timedelta(days=i)
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
