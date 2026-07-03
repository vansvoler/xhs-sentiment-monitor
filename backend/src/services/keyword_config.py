"""
监控关键词配置

关键词从 ``.env`` 挪到 MongoDB ``monitor_keywords``，运行时可增删，下一轮
``collect_keywords`` 即生效。首次（集合为空）自动从 ``.env`` 的三组关键词播种，
保证既有配置不丢。一个关键词只属于一个分类（brand/competitor/industry）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from src.config import settings
from src.db.mongodb import mongodb

CATEGORIES = ("brand", "competitor", "industry")


class KeywordConfigService:
    """监控关键词的持久化读写"""

    @property
    def _coll(self):
        return mongodb.get_collection("monitor_keywords")

    async def seed_if_empty(self) -> None:
        """集合为空时从 .env 播种（DB 未初始化则跳过）"""
        if mongodb.db is None:
            return
        if await self._coll.estimated_document_count() > 0:
            return
        seed = {
            "brand": settings.MONITOR_KEYWORDS_BRAND,
            "competitor": settings.MONITOR_KEYWORDS_COMPETITOR,
            "industry": settings.MONITOR_KEYWORDS_INDUSTRY,
        }
        now = datetime.utcnow()
        docs = []
        seen: set[str] = set()
        for cat, words in seed.items():
            for w in words:
                if w and w not in seen:
                    seen.add(w)
                    docs.append({"keyword": w, "category": cat, "created_at": now})
        if docs:
            await self._coll.insert_many(docs)

    async def list_grouped(self) -> Dict[str, List[str]]:
        """返回 {brand, competitor, industry, all}"""
        groups: Dict[str, List[str]] = {c: [] for c in CATEGORIES}
        all_words: List[str] = []
        async for d in self._coll.find({}, {"_id": 0}).sort("created_at", 1):
            cat, kw = d.get("category"), d.get("keyword")
            if cat in groups and kw:
                groups[cat].append(kw)
                all_words.append(kw)
        return {**groups, "all": all_words}

    async def category_map(self) -> Dict[str, str]:
        """{keyword: category}，供采集器遍历"""
        result: Dict[str, str] = {}
        async for d in self._coll.find(
            {}, {"_id": 0, "keyword": 1, "category": 1}
        ):
            kw, cat = d.get("keyword"), d.get("category")
            if kw and cat:
                result.setdefault(kw, cat)
        return result

    async def add(self, keyword: str, category: str) -> None:
        keyword = keyword.strip()
        if not keyword:
            raise ValueError("关键词不能为空")
        if category not in CATEGORIES:
            raise ValueError(f"分类必须是 {CATEGORIES} 之一")
        await self._coll.update_one(
            {"keyword": keyword},
            {
                "$set": {"category": category},
                "$setOnInsert": {"created_at": datetime.utcnow()},
            },
            upsert=True,
        )

    async def remove(self, keyword: str) -> bool:
        res = await self._coll.delete_one({"keyword": keyword})
        return res.deleted_count > 0


keyword_config = KeywordConfigService()
