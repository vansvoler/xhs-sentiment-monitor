"""
KOL 挖掘服务

免费阶段：聚合存量笔记的作者 → 相关度/互动/情感打分 → 候选池。
人工态（status/remark）与富化结果（粉丝数等）持久化在 ``kol_profiles``，
按 user_id 与实时聚合结果合并。粉丝数需付费富化，见 ``enrich``。
"""
from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.config import settings
from src.db.mongodb import mongodb
from src.models.kol import KolCandidate, KolStatus

logger = logging.getLogger(__name__)

# 打分权重
_W_RELEVANCE = 0.40
_W_ENGAGEMENT = 0.35
_W_SENTIMENT = 0.25
# 互动归一：篇均互动达到该值即满分
_ENGAGEMENT_CEIL = 5000


def _relevance(note_count: int, kw_hit: int) -> float:
    return min(note_count / 8, 1) * 70 + min(kw_hit / 3, 1) * 30


def _engagement(avg_eng: float) -> float:
    return min(math.log10(avg_eng + 1) / math.log10(_ENGAGEMENT_CEIL + 1), 1) * 100


class KolDiscoveryService:
    """KOL 候选挖掘"""

    @property
    def _notes(self):
        return mongodb.get_collection("notes")

    @property
    def _profiles(self):
        return mongodb.get_collection("kol_profiles")

    # ---------------- 挖掘 ----------------
    async def discover(  # noqa: PLR0913
        self,
        *,
        min_notes: int = 2,
        keyword: Optional[str] = None,
        min_engagement: float = 0.0,
        sentiment: Optional[str] = None,
        hide_own: bool = True,
        hide_competitor: bool = False,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[KolCandidate]:
        """聚合作者并打分，合并人工态后过滤/排序"""
        raw = await self._aggregate_authors(min_notes)
        profiles = await self._load_profiles([r["_id"] for r in raw])

        candidates: List[KolCandidate] = []
        for r in raw:
            c = self._build_candidate(r, profiles.get(r["_id"], {}))
            if self._passes(
                c, keyword, min_engagement, sentiment, hide_own, hide_competitor,
                status,
            ):
                candidates.append(c)

        candidates.sort(key=lambda x: x.fit_score, reverse=True)
        return candidates[:limit]

    async def _aggregate_authors(self, min_notes: int) -> List[Dict[str, Any]]:
        cursor = self._notes.aggregate([
            {"$match": {"author.user_id": {"$nin": ["", None]}}},
            {"$group": {
                "_id": "$author.user_id",
                "nickname": {"$last": "$author.nickname"},
                "avatar": {"$last": "$author.avatar"},
                "note_count": {"$sum": 1},
                "keywords_hit": {"$addToSet": "$search_keyword"},
                "total_engagement": {"$sum": {"$add": [
                    {"$ifNull": ["$stats.likes", 0]},
                    {"$ifNull": ["$stats.comments", 0]},
                    {"$ifNull": ["$stats.collects", 0]},
                ]}},
                "positive": {"$sum": {"$cond": [
                    {"$eq": ["$sentiment.label", "positive"]}, 1, 0]}},
                "score_sum": {"$sum": {"$ifNull": ["$sentiment.score", 0.5]}},
                "last_post_at": {"$max": "$published_at"},
            }},
            {"$match": {"note_count": {"$gte": min_notes}}},
        ])
        return [r async for r in cursor]

    async def _load_profiles(self, uids: List[str]) -> Dict[str, Dict[str, Any]]:
        cursor = self._profiles.find({"user_id": {"$in": uids}}, {"_id": 0})
        return {p["user_id"]: p async for p in cursor}

    def _build_candidate(
        self, r: Dict[str, Any], profile: Dict[str, Any]
    ) -> KolCandidate:
        n = r["note_count"]
        kws = [k for k in (r.get("keywords_hit") or []) if k]
        avg_eng = r["total_engagement"] / n if n else 0.0
        positive_rate = r["positive"] / n if n else 0.0
        avg_sent = r["score_sum"] / n if n else 0.5

        is_own = self._is_own(r.get("nickname") or "")
        is_competitor = self._is_competitor(kws, is_own)

        rel = _relevance(n, len(kws))
        eng = _engagement(avg_eng)
        sen = positive_rate * 100
        fit = _W_RELEVANCE * rel + _W_ENGAGEMENT * eng + _W_SENTIMENT * sen
        if is_competitor:
            fit *= 0.2

        return KolCandidate(
            user_id=r["_id"],
            nickname=r.get("nickname") or "",
            avatar=r.get("avatar"),
            note_count=n,
            keywords_hit=kws,
            avg_engagement=round(avg_eng, 1),
            positive_rate=round(positive_rate, 3),
            avg_sentiment_score=round(avg_sent, 3),
            last_post_at=r.get("last_post_at"),
            is_own=is_own,
            is_competitor=is_competitor,
            fit_score=round(fit, 1),
            score_breakdown={
                "relevance": round(rel, 1),
                "engagement": round(eng, 1),
                "sentiment": round(sen, 1),
            },
            # 富化 + 人工态（来自 profile）
            fans_count=profile.get("fans_count"),
            verified=profile.get("verified"),
            bio=profile.get("bio"),
            ip_location=profile.get("ip_location"),
            enriched_at=profile.get("enriched_at"),
            status=KolStatus(profile.get("status", "candidate")),
            remark=profile.get("remark"),
        )

    @staticmethod
    def _is_own(nickname: str) -> bool:
        return any(m in nickname for m in settings.KOL_OWN_ACCOUNT_MARKERS)

    @staticmethod
    def _is_competitor(kws: List[str], is_own: bool) -> bool:
        if is_own or not kws:
            return False
        comp = set(settings.MONITOR_KEYWORDS_COMPETITOR)
        return bool(comp) and all(k in comp for k in kws)

    @staticmethod
    def _passes(  # noqa: PLR0913
        c: KolCandidate,
        keyword: Optional[str],
        min_engagement: float,
        sentiment: Optional[str],
        hide_own: bool,
        hide_competitor: bool,
        status: Optional[str],
    ) -> bool:
        if hide_own and c.is_own:
            return False
        if hide_competitor and c.is_competitor:
            return False
        if keyword and keyword not in c.keywords_hit:
            return False
        if c.avg_engagement < min_engagement:
            return False
        if sentiment == "positive" and c.positive_rate < 0.5:
            return False
        if status and c.status.value != status:
            return False
        return True

    # ---------------- 人工态 ----------------
    async def set_status(
        self, user_id: str, status: str, remark: Optional[str] = None
    ) -> None:
        update: Dict[str, Any] = {"status": KolStatus(status).value}
        if remark is not None:
            update["remark"] = remark
        await self._profiles.update_one(
            {"user_id": user_id}, {"$set": update}, upsert=True
        )

    # ---------------- 富化（付费）----------------
    async def enrich(self, user_id: str) -> Dict[str, Any]:
        """对单个候选补粉丝数等信息；受每日上限约束，结果缓存。

        依赖 TikHub `get_user_info`（付费）。字段映射在 TikHub 充值联通后需按
        实际响应校对，见 collectors/tikhub.py。
        """
        existing = await self._profiles.find_one({"user_id": user_id})
        if existing and existing.get("enriched_at"):
            return {"cached": True, "profile": {k: v for k, v in existing.items()
                                                if k != "_id"}}

        if not await self._within_daily_limit():
            raise RuntimeError(
                f"今日富化已达上限 {settings.KOL_ENRICH_DAILY_LIMIT} 次"
            )

        from src.collectors.tikhub import tikhub_client
        info = await tikhub_client.get_user_info(user_id)
        patch = {
            "fans_count": info.get("fans_count"),
            "verified": info.get("verified"),
            "bio": info.get("bio"),
            "ip_location": info.get("ip_location"),
            "enriched_at": datetime.utcnow(),
        }
        await self._profiles.update_one(
            {"user_id": user_id}, {"$set": patch}, upsert=True
        )
        return {"cached": False, "profile": patch}

    async def _within_daily_limit(self) -> bool:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        used = await self._profiles.count_documents({"enriched_at": {"$gte": today}})
        return used < settings.KOL_ENRICH_DAILY_LIMIT


kol_discovery = KolDiscoveryService()
