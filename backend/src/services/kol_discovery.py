"""
KOL 挖掘服务

免费阶段：聚合存量笔记的作者 → 关联度/互动打分 → 候选池。
人工态（status/remark）与富化结果（粉丝数等）持久化在 ``kol_profiles``，
按 user_id 与实时聚合结果合并。粉丝数需付费富化，见 ``enrich``。

打分只看两件事：**内容关联性**（命中词离品牌多近 × 发文深度）与 **笔记数据**
（篇均互动）。情感不入分——一个中性口吻的高质量作者与一个负面作者，在招募
价值上不该被一视同仁地归零；正面率仅作列表展示，供人工参考。
"""
from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.config import settings
from src.db.filters import ON_TOPIC
from src.db.mongodb import mongodb
from src.models.kol import AccountType, KolCandidate, KolNote, KolStatus
from src.services.keyword_config import keyword_config

logger = logging.getLogger(__name__)

# 打分权重：关联度与互动各半
_W_RELEVANCE = 0.5
_W_ENGAGEMENT = 0.5

# 命中词类型分——离品牌越近，招募价值越高
_CATEGORY_SCORE = {"brand": 100.0, "competitor": 75.0, "industry": 55.0}

# 互动归一：篇均互动达到该值即满分。取自库内 on_topic 作者篇均互动的 P90
# （≈1395），国际教育垂类的头部线，不与全平台美妆博主对齐。
_ENGAGEMENT_CEIL = 1500

# 发文深度归一：发满该篇数即拿满深度增益
_DEPTH_FULL = 10
# 深度只调节关联度的这一段，单篇作者仍保留 (1 - _DEPTH_SWING) 的基础分，
# 避免"一篇高质量笔记"被"八篇水贴"压死。
_DEPTH_SWING = 0.3


def _relevance(note_count: int, top_category: str) -> float:
    """关联度 = 命中词类型分 × 发文深度增益"""
    base = _CATEGORY_SCORE.get(top_category, _CATEGORY_SCORE["industry"])
    depth = min(math.log10(note_count + 1) / math.log10(_DEPTH_FULL + 1), 1)
    return base * (1 - _DEPTH_SWING + _DEPTH_SWING * depth)


def _engagement(avg_eng: float) -> float:
    return min(math.log10(avg_eng + 1) / math.log10(_ENGAGEMENT_CEIL + 1), 1) * 100


def _top_category(kws: List[str], cat_map: Dict[str, str]) -> str:
    """取命中词里最靠近品牌的一类"""
    cats = [cat_map[k] for k in kws if k in cat_map]
    return max(cats, key=lambda c: _CATEGORY_SCORE.get(c, 0), default="industry")


# 不指定 status 时的默认视图：已排除的不出现
_DEFAULT_STATUSES = {KolStatus.CANDIDATE.value, KolStatus.SHORTLISTED.value}


def _status(raw: Optional[str]) -> KolStatus:
    """容忍库里的历史态，未知一律视作未处理"""
    try:
        return KolStatus(raw or "candidate")
    except ValueError:
        return KolStatus.CANDIDATE


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
        min_notes: int = 1,
        keyword: Optional[str] = None,
        nickname: Optional[str] = None,
        min_engagement: float = 0.0,
        account_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[KolCandidate]:
        """聚合作者并打分，合并人工态后过滤/排序"""
        cat_map = await keyword_config.category_map()
        raw = await self._aggregate_authors(min_notes, list(cat_map))
        profiles = await self._load_profiles([r["_id"] for r in raw])

        candidates = [
            self._build_candidate(r, profiles.get(r["_id"], {}), cat_map) for r in raw
        ]
        candidates = [
            c for c in candidates
            if self._passes(c, keyword, nickname, min_engagement, account_type, status)
        ]
        candidates.sort(key=lambda x: x.fit_score, reverse=True)
        return candidates[:limit]

    async def _aggregate_authors(
        self, min_notes: int, keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """按 user_id 聚合。只算当前监控词下的笔记，历史孤儿词自动出局。"""
        cursor = self._notes.aggregate([
            {"$match": {
                **ON_TOPIC,
                "author.user_id": {"$nin": ["", None]},
                "search_keyword": {"$in": keywords},
            }},
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
        self, r: Dict[str, Any], profile: Dict[str, Any], cat_map: Dict[str, str]
    ) -> KolCandidate:
        n = r["note_count"]
        kws = [k for k in (r.get("keywords_hit") or []) if k]
        avg_eng = r["total_engagement"] / n if n else 0.0
        top_cat = _top_category(kws, cat_map)

        rel = _relevance(n, top_cat)
        eng = _engagement(avg_eng)
        fit = _W_RELEVANCE * rel + _W_ENGAGEMENT * eng

        # 人工校正永远胜出：昵称规则只是启发式，看走眼时以人的判断为准
        manual = profile.get("account_type")
        auto = self._account_type(r.get("nickname") or "", cat_map)

        return KolCandidate(
            user_id=r["_id"],
            nickname=r.get("nickname") or "",
            avatar=r.get("avatar"),
            note_count=n,
            keywords_hit=kws,
            top_category=top_cat,
            avg_engagement=round(avg_eng, 1),
            last_post_at=r.get("last_post_at"),
            positive_rate=round(r["positive"] / n if n else 0.0, 3),
            avg_sentiment_score=round(r["score_sum"] / n if n else 0.5, 3),
            account_type=AccountType(manual) if manual else auto,
            account_type_manual=bool(manual),
            fit_score=round(fit, 1),
            score_breakdown={"relevance": round(rel, 1), "engagement": round(eng, 1)},
            # 富化 + 人工态（来自 profile）
            fans_count=profile.get("fans_count"),
            verified=profile.get("verified"),
            bio=profile.get("bio"),
            ip_location=profile.get("ip_location"),
            enriched_at=profile.get("enriched_at"),
            status=_status(profile.get("status")),
            remark=profile.get("remark"),
        )

    @staticmethod
    def _account_type(nickname: str, cat_map: Dict[str, str]) -> AccountType:
        """昵称含机构名 → 官号/员工号；判不出一律当素人"""
        name = nickname.lower()
        own = set(settings.KOL_OWN_ACCOUNT_MARKERS) | {
            k for k, c in cat_map.items() if c == "brand"
        }
        if any(w.lower() in name for w in own if w):
            return AccountType.OWN_MATRIX
        rivals = {k for k, c in cat_map.items() if c == "competitor"}
        if any(w.lower() in name for w in rivals if w):
            return AccountType.COMPETITOR_MATRIX
        return AccountType.INDIVIDUAL

    @staticmethod
    def _passes(  # noqa: PLR0913
        c: KolCandidate,
        keyword: Optional[str],
        nickname: Optional[str],
        min_engagement: float,
        account_type: Optional[str],
        status: Optional[str],
    ) -> bool:
        # 不指定状态时"全部"= 候选 + 名单，已排除的只在点开该 tab 时才现身
        allowed = {status} if status else _DEFAULT_STATUSES
        if c.status.value not in allowed:
            return False
        if keyword and keyword not in c.keywords_hit:
            return False
        if nickname and nickname.lower() not in (c.nickname or "").lower():
            return False
        if c.avg_engagement < min_engagement:
            return False
        if account_type and c.account_type.value != account_type:
            return False
        return True

    # ---------------- 相关笔记 ----------------
    async def author_notes(self, user_id: str, limit: int = 50) -> List[KolNote]:
        """该作者命中当前监控词的笔记，新的在前——分数的原始依据"""
        cat_map = await keyword_config.category_map()
        cursor = self._notes.find(
            {
                **ON_TOPIC,
                "author.user_id": user_id,
                "search_keyword": {"$in": list(cat_map)},
            },
        ).sort("published_at", -1).limit(limit)
        return [
            KolNote(
                note_id=d.get("note_id", ""),
                xsec_token=d.get("xsec_token"),
                title=d.get("title") or "",
                search_keyword=d.get("search_keyword") or "",
                published_at=d.get("published_at"),
                likes=(d.get("stats") or {}).get("likes", 0),
                comments=(d.get("stats") or {}).get("comments", 0),
                collects=(d.get("stats") or {}).get("collects", 0),
                sentiment=(d.get("sentiment") or {}).get("label"),
            )
            async for d in cursor
        ]

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

    async def set_account_type(self, user_id: str, account_type: str) -> None:
        """人工校正账号分类；传空串则撤销校正，交还给昵称规则"""
        patch = (
            {"$unset": {"account_type": ""}} if not account_type
            else {"$set": {"account_type": AccountType(account_type).value}}
        )
        await self._profiles.update_one({"user_id": user_id}, patch, upsert=True)

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
