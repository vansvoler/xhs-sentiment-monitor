"""
任务调度器

周期性任务：
- collect_keywords    关键词 → 搜索 → 详情 → 入库 → 推送新笔记
- collect_comments    已采笔记 → 拉评论 → 入库
- analyze_sentiment   未分析的 notes/comments → Senta → 回写 → 推送；判负即告警
- scan_alerts         按关键词扫负面率/声量突增 → alerts
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from apscheduler.schedulers.asyncio import (  # type: ignore[import-untyped]
    AsyncIOScheduler,
)
from apscheduler.triggers.interval import (  # type: ignore[import-untyped]
    IntervalTrigger,
)

from src.analyzers.senta_service import get_sentiment_service
from src.collectors.xhs_api import DataCollector
from src.config import settings
from src.db.mongodb import mongodb
from src.services.alert_service import alert_service
from src.services.keyword_config import keyword_config
from src.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_collector = DataCollector()


# ================ 任务 1: 关键词采集 ================
async def collect_keywords() -> None:
    """遍历监控关键词，搜索新笔记并入库"""
    kw_map = await keyword_config.category_map()
    if not kw_map:
        logger.debug("监控关键词为空，跳过关键词采集")
        return

    logger.info("开始关键词采集，共 %d 个关键词", len(kw_map))
    for keyword, category in kw_map.items():
        try:
            new_ids = await _collector.collect_and_upsert_by_keyword(keyword, category)
        except Exception as e:  # 防止一个关键词失败影响其他
            logger.exception("关键词 %s 采集异常: %s", keyword, e)
            continue

        # 广播新笔记
        for note_id in new_ids:
            note = await mongodb.get_collection("notes").find_one({"note_id": note_id})
            if note:
                note.pop("_id", None)
                await websocket_manager.send_new_note(note)


# ================ 任务 2: 评论采集 ================
async def collect_comments() -> None:
    """为需要刷新评论的笔记拉评论"""
    threshold = datetime.utcnow() - timedelta(hours=settings.COMMENTS_REFRESH_HOURS)
    notes_coll = mongodb.get_collection("notes")

    # 找出 comments_collected_at 缺失 或 早于阈值 的笔记
    cursor = notes_coll.find(
        {
            "$or": [
                {"comments_collected_at": {"$exists": False}},
                {"comments_collected_at": {"$lt": threshold}},
            ]
        },
        {"note_id": 1},
    ).limit(20)

    targets = [doc["note_id"] async for doc in cursor if doc.get("note_id")]
    if not targets:
        logger.debug("无需刷新评论的笔记")
        return

    logger.info("开始评论采集，共 %d 条笔记", len(targets))
    for note_id in targets:
        try:
            await _collector.collect_note_comments(note_id)
        except Exception as e:
            logger.exception("笔记 %s 评论采集异常: %s", note_id, e)


# ================ 任务 3: 情感分析 ================
async def analyze_sentiment() -> None:
    """为缺失 sentiment 的 notes/comments 批量补齐"""
    senta = get_sentiment_service()
    batch_size = settings.SENTIMENT_BATCH_SIZE

    await _analyze_collection(
        "notes",
        text_builder=lambda d: f"{d.get('title','')} {d.get('content','')}".strip(),
        broadcast=lambda doc, result: websocket_manager.send_sentiment_update(
            {"note_id": doc["note_id"], "sentiment": result}
        ),
        alert_eval=lambda doc: alert_service.evaluate_note(doc),
        senta=senta,
        batch_size=batch_size,
    )
    await _analyze_collection(
        "comments",
        text_builder=lambda d: d.get("content", ""),
        broadcast=None,
        alert_eval=lambda doc: alert_service.evaluate_comment(doc),
        senta=senta,
        batch_size=batch_size,
    )


async def _analyze_collection(  # noqa: PLR0913
    collection_name: str,
    *,
    text_builder,
    broadcast,
    alert_eval,
    senta,
    batch_size: int,
) -> None:
    """批处理一个集合内缺失 sentiment 的文档"""
    coll = mongodb.get_collection(collection_name)
    cursor = coll.find({"sentiment": {"$exists": False}}).limit(batch_size)
    docs: List[Dict[str, Any]] = [d async for d in cursor]
    if not docs:
        return

    id_field = "note_id" if collection_name == "notes" else "comment_id"
    _neutral = {"label": "neutral", "score": 0.5, "emotion": "neutral"}

    texts = [text_builder(d) for d in docs]
    valid_indices = [i for i, t in enumerate(texts) if t.strip()]

    # 空文本统一标中性，避免每轮重复扫描（含全空批次）
    for idx, doc in enumerate(docs):
        if idx not in set(valid_indices):
            await coll.update_one(
                {id_field: doc[id_field]}, {"$set": {"sentiment": _neutral}}
            )
    if not valid_indices:
        return

    results = senta.batch_analyze([texts[i] for i in valid_indices])
    alerts = []
    for idx, result in zip(valid_indices, results):
        doc = docs[idx]
        sentiment_doc = (
            result.model_dump() if hasattr(result, "model_dump") else result.dict()
        )
        await coll.update_one(
            {id_field: doc[id_field]}, {"$set": {"sentiment": sentiment_doc}}
        )
        if broadcast is not None:
            await broadcast(doc, sentiment_doc)
        alert = alert_eval({**doc, "sentiment": sentiment_doc})
        if alert is not None:
            alerts.append(alert)

    created = await alert_service.emit(alerts) if alerts else 0
    logger.info(
        "%s 情感分析完成 %d 条，触发告警 %d 条",
        collection_name, len(valid_indices), created,
    )


async def scan_alerts_job() -> None:
    """周期扫描关键词负面率 / 声量突增，产出告警。"""
    try:
        alerts = await alert_service.scan_keyword_health()
        created = await alert_service.emit(alerts)
    except Exception as e:
        logger.exception("舆情告警扫描异常: %s", e)
        return
    logger.info("舆情告警扫描完成，检出 %d 条，新增 %d 条", len(alerts), created)


# ================ 调度控制 ================
def start_scheduler() -> None:
    """启动三个周期任务"""
    scheduler.add_job(
        collect_keywords,
        trigger=IntervalTrigger(minutes=settings.COLLECT_INTERVAL_MINUTES),
        id="collect_keywords",
        name="关键词采集",
        replace_existing=True,
        next_run_time=datetime.utcnow()
        + timedelta(seconds=10),  # 启动 10s 后立即跑一次
    )
    scheduler.add_job(
        collect_comments,
        trigger=IntervalTrigger(minutes=settings.COLLECT_INTERVAL_MINUTES),
        id="collect_comments",
        name="评论采集",
        replace_existing=True,
    )
    scheduler.add_job(
        analyze_sentiment,
        trigger=IntervalTrigger(minutes=15),
        id="analyze_sentiment",
        name="情感分析",
        replace_existing=True,
        next_run_time=datetime.utcnow()
        + timedelta(seconds=30),  # 启动 30s 后立即跑一次
    )
    scheduler.add_job(
        scan_alerts_job,
        trigger=IntervalTrigger(minutes=settings.ALERT_SCAN_INTERVAL_MINUTES),
        id="scan_alerts",
        name="舆情告警扫描",
        replace_existing=True,
        next_run_time=datetime.utcnow() + timedelta(seconds=50),
    )
    scheduler.start()
    logger.info("任务调度器已启动")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("任务调度器已停止")
