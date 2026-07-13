"""
舆情预警服务

三类告警：
- negative_note / negative_comment：单条负面内容实时触发，高影响力作者升级 critical。
- negative_rate：关键词在窗口内负面率超阈值。
- volume_spike：关键词声量相对上一窗口突增。

去重：每条告警有 ``alert_id``，按天 + 类型 + 关键词分桶，同一事件当天只入库并推送一次。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.config import settings
from src.db.filters import ON_TOPIC
from src.db.mongodb import mongodb
from src.models.alert import Alert, AlertLevel, AlertStatus, AlertType
from src.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


def _neg_count_expr() -> Dict[str, Any]:
    return {"$sum": {"$cond": [{"$eq": ["$sentiment.label", "negative"]}, 1, 0]}}


class AlertService:
    """舆情告警检测 + 持久化 + 推送"""

    @property
    def _coll(self):
        return mongodb.get_collection("alerts")

    # ---------------- 单条内容 ----------------
    def evaluate_note(self, note: Dict[str, Any]) -> Optional[Alert]:
        """负面笔记 → 告警；高影响力作者升级为 critical"""
        sentiment = note.get("sentiment") or {}
        if sentiment.get("label") != "negative":
            return None
        score = float(sentiment.get("score", 0))
        if score < settings.ALERT_NEGATIVE_SCORE_MIN:
            return None

        fans = int((note.get("author") or {}).get("fans_count", 0))
        high = fans >= settings.ALERT_HIGH_INFLUENCE_FANS
        note_id = note.get("note_id", "")
        title = note.get("title") or note.get("content", "")[:30]
        return Alert(
            alert_id=f"negative_note:{note_id}",
            type=AlertType.NEGATIVE_NOTE,
            level=AlertLevel.CRITICAL if high else AlertLevel.WARNING,
            title=f"负面笔记（{fans} 粉丝）" if high else "负面笔记",
            message=title,
            keyword=note.get("search_keyword"),
            note_id=note_id,
            sentiment_score=score,
            metric={"fans_count": fans},
        )

    def evaluate_comment(self, comment: Dict[str, Any]) -> Optional[Alert]:
        """负面评论 → 告警"""
        sentiment = comment.get("sentiment") or {}
        if sentiment.get("label") != "negative":
            return None
        score = float(sentiment.get("score", 0))
        if score < settings.ALERT_NEGATIVE_SCORE_MIN:
            return None
        return Alert(
            alert_id=f"negative_comment:{comment.get('comment_id', '')}",
            type=AlertType.NEGATIVE_COMMENT,
            level=AlertLevel.WARNING,
            title="负面评论",
            message=comment.get("content", "")[:50],
            note_id=comment.get("note_id"),
            sentiment_score=score,
        )

    # ---------------- 关键词健康扫描 ----------------
    async def scan_keyword_health(
        self, reference_time: Optional[datetime] = None
    ) -> List[Alert]:
        """按关键词扫描负面率与声量突增；reference_time 便于测试历史窗口"""
        now = reference_time or datetime.utcnow()
        window = timedelta(hours=settings.ALERT_SCAN_HOURS)
        cur = await self._keyword_window(now - window, now, with_negative=True)
        prev = await self._keyword_window(now - 2 * window, now - window)

        alerts: List[Alert] = []
        day = now.strftime("%Y%m%d")
        for kw, stat in cur.items():
            volume = stat["volume"]
            if volume < settings.ALERT_MIN_VOLUME:
                continue

            rate = stat["negative"] / volume
            if rate >= settings.ALERT_NEGATIVE_RATE_THRESHOLD:
                alerts.append(Alert(
                    alert_id=f"negative_rate:{kw}:{day}",
                    type=AlertType.NEGATIVE_RATE,
                    level=AlertLevel.CRITICAL if rate >= 0.5 else AlertLevel.WARNING,
                    title=f"「{kw}」负面率 {rate:.0%}",
                    message=f"近 {settings.ALERT_SCAN_HOURS}h 共 {volume} 条，"
                            f"其中负面 {stat['negative']} 条",
                    keyword=kw,
                    metric={"negative_rate": round(rate, 3), "volume": volume},
                ))

            base = prev.get(kw, {}).get("volume", 0)
            if base > 0 and volume / base >= settings.ALERT_SPIKE_RATIO:
                ratio = volume / base
                alerts.append(Alert(
                    alert_id=f"volume_spike:{kw}:{day}",
                    type=AlertType.VOLUME_SPIKE,
                    level=AlertLevel.WARNING,
                    title=f"「{kw}」声量突增 {ratio:.1f}×",
                    message=f"近 {settings.ALERT_SCAN_HOURS}h {volume} 条，"
                            f"上一窗口 {base} 条",
                    keyword=kw,
                    metric={"volume": volume, "baseline": base,
                            "ratio": round(ratio, 2)},
                ))
        return alerts

    async def _keyword_window(
        self, start: datetime, end: datetime, with_negative: bool = False
    ) -> Dict[str, Dict[str, int]]:
        group: Dict[str, Any] = {"_id": "$search_keyword", "volume": {"$sum": 1}}
        if with_negative:
            group["negative"] = _neg_count_expr()
        cursor = mongodb.get_collection("notes").aggregate(
            [
                {"$match": {**ON_TOPIC, "search_keyword": {"$ne": None},
                            "published_at": {"$gte": start, "$lt": end}}},
                {"$group": group},
            ]
        )
        return {
            r["_id"]: {"volume": r["volume"], "negative": r.get("negative", 0)}
            async for r in cursor
        }

    # ---------------- 持久化 + 推送 ----------------
    async def save_and_broadcast(self, alert: Alert) -> bool:
        """按 alert_id 去重 upsert；仅首次入库时推送。返回是否为新告警"""
        doc = alert.model_dump()
        res = await self._coll.update_one(
            {"alert_id": alert.alert_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        if res.upserted_id is None:
            return False
        await websocket_manager.send_alert(doc)
        logger.info("新告警 [%s] %s", alert.level.value, alert.title)
        return True

    async def emit(self, alerts: List[Alert]) -> int:
        """批量落库 + 推送，返回新告警条数"""
        created = 0
        for a in alerts:
            if await self.save_and_broadcast(a):
                created += 1
        return created

    # ---------------- 查询 ----------------
    async def list_alerts(
        self,
        status: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if status:
            query["status"] = status
        if level:
            query["level"] = level
        cursor = self._coll.find(query, {"_id": 0}).sort(
            "created_at", -1
        ).limit(limit)
        return [doc async for doc in cursor]

    async def acknowledge(self, alert_id: str) -> bool:
        res = await self._coll.update_one(
            {"alert_id": alert_id},
            {"$set": {"status": AlertStatus.ACKNOWLEDGED.value}},
        )
        return res.modified_count > 0


alert_service = AlertService()
