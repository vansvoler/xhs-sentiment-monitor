"""
任务调度器

每天北京时间 DAILY_COLLECT_HOUR 点跑一次 ``daily_collect``：
  关键词采集 → 入库/广播 → LLM 情感+相关性分析 → 告警扫描（串在一个批次里）。
启动补采：错过当天采集点且今天没采过时立即补一次（重启不重复扣费）。
评论采集（collect_comments）默认关停，见 ENABLE_COMMENT_COLLECTION。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from apscheduler.schedulers.asyncio import (  # type: ignore[import-untyped]
    AsyncIOScheduler,
)
from apscheduler.triggers.cron import (  # type: ignore[import-untyped]
    CronTrigger,
)

from src.analyzers.sentiment_service import get_sentiment_service
from src.collectors.xhs_api import DataCollector
from src.config import settings
from src.db.mongodb import mongodb
from src.services.alert_service import alert_service
from src.services.keyword_config import keyword_config
from src.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)

# timezone=UTC：代码里的 next_run_time 用 datetime.utcnow()（朴素 UTC），
#   必须让调度器也按 UTC 解释，否则会被当成本机时区（CST）导致任务"过期"跳过。
# misfire_grace_time：任务晚到 5 分钟内仍执行；coalesce：多次错过只补跑一次。
scheduler = AsyncIOScheduler(
    timezone="UTC",
    job_defaults={"misfire_grace_time": 300, "coalesce": True},
)
_collector = DataCollector()


_CST = timezone(timedelta(hours=8))


# ================ 每日批次：采集 → 分析 → 告警 ================
async def daily_collect() -> None:
    """每天一次的完整流水：关键词采集 → 情感/相关性分析 → 告警扫描。

    采完立即分析，保证"8 点抓、9 点前出结果"。TikHub 每次调用都扣费，
    故记录 ``job_state.last_run_at``，供启动补采判断"今天是否已采过"。
    """
    kw_map = await keyword_config.category_map()
    if not kw_map:
        logger.debug("监控关键词为空，跳过每日采集")
        return

    logger.info("开始每日采集，共 %d 个关键词", len(kw_map))
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

    # 采完立即分析 + 扫告警，串在同一批次里出结果
    await analyze_sentiment()
    await scan_alerts_job()

    await mongodb.get_collection("job_state").update_one(
        {"_id": "collect_keywords"},
        {"$set": {"last_run_at": datetime.utcnow()}},
        upsert=True,
    )
    logger.info("每日采集+分析完成")


def _today_collect_utc() -> datetime:
    """今天北京时间 DAILY_COLLECT_HOUR 点，换算成朴素 UTC"""
    local = datetime.now(_CST).replace(
        hour=settings.DAILY_COLLECT_HOUR, minute=0, second=0, microsecond=0
    )
    return local.astimezone(timezone.utc).replace(tzinfo=None)


async def _needs_catchup() -> bool:
    """启动补采：今天的采集点已过、且今天还没采过 → 立即补一次。

    重启若今天已采过则返回 False（不重复扣费）；机器 8 点没开、后来才开机
    则返回 True 补采当天数据。
    """
    scheduled = _today_collect_utc()
    if datetime.utcnow() < scheduled:
        return False  # 还没到今天的采集点，等 cron
    doc = await mongodb.get_collection("job_state").find_one(
        {"_id": "collect_keywords"}
    )
    last = (doc or {}).get("last_run_at")
    return last is None or last < scheduled


# ================ 任务 2: 评论采集 ================
async def collect_comments() -> None:
    """只为新增的品牌/行业笔记拉一次评论。

    - 抓 ``COMMENT_CATEGORIES`` 内分类（品牌/竞品/行业）的笔记评论。
    - 笔记采集满 ``COMMENT_DELAY_HOURS`` 小时后才拉评论（给评论累积时间）。
    - 评论数低于 ``COMMENT_MIN_COMMENTS`` 的笔记跳过（零评论没舆情可看，省调用）。
    - 只抓从未采过评论的笔记（``comments_collected_at`` 缺失），采一次即止、不刷新；
      历史笔记在部署时已统一标记为"已采"，因此只有后续新增的笔记会命中。
    """
    notes_coll = mongodb.get_collection("notes")
    ready = datetime.utcnow() - timedelta(hours=settings.COMMENT_DELAY_HOURS)

    cursor = notes_coll.find(
        {
            "comments_collected_at": {"$exists": False},
            "category": {"$in": settings.COMMENT_CATEGORIES},
            "collected_at": {"$lte": ready},
            "stats.comments": {"$gte": settings.COMMENT_MIN_COMMENTS},
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

    max_per_run = settings.SENTIMENT_MAX_PER_RUN
    await _analyze_collection(
        "notes",
        text_builder=lambda d: f"{d.get('title','')} {d.get('content','')}".strip(),
        keyword_builder=lambda d: d.get("search_keyword") or "",
        broadcast=lambda doc, result: websocket_manager.send_sentiment_update(
            {"note_id": doc["note_id"], "sentiment": result}
        ),
        alert_eval=lambda doc: alert_service.evaluate_note(doc),
        senta=senta,
        batch_size=batch_size,
        max_docs=max_per_run,
    )
    await _analyze_collection(
        "comments",
        text_builder=lambda d: d.get("content", ""),
        keyword_builder=None,
        broadcast=None,
        alert_eval=lambda doc: alert_service.evaluate_comment(doc),
        senta=senta,
        batch_size=batch_size,
        max_docs=max_per_run,
    )


def _pending_query(senta, with_relevance: bool) -> Dict[str, Any]:
    """待分析文档的查询条件。

    LLM 服务可判语义相关性：把缺 ``relevance`` 的存量笔记也纳入，
    逐轮回填（每轮 max_docs 条），无需单独的回填脚本。
    """
    missing_sentiment: Dict[str, Any] = {"sentiment": {"$exists": False}}
    if with_relevance and senta.supports_relevance:
        return {"$or": [missing_sentiment, {"relevance": {"$exists": False}}]}
    return missing_sentiment


async def _analyze_collection(  # noqa: PLR0913
    collection_name: str,
    *,
    text_builder,
    keyword_builder,
    broadcast,
    alert_eval,
    senta,
    batch_size: int,
    max_docs: int,
) -> None:
    """循环抽干集合内待分析的文档，最多处理 max_docs 条。

    按 ``collected_at`` 倒序：最新采集的先分析，保证近期舆情始终是最新的。
    带 keyword_builder（笔记）时同时写 ``relevance``（on_topic/off_topic）；
    广播与告警只针对"首次分析且相关"的文档，回填存量时保持安静。
    """
    coll = mongodb.get_collection(collection_name)
    id_field = "note_id" if collection_name == "notes" else "comment_id"
    neutral = {"label": "neutral", "score": 0.5, "emotion": "neutral"}
    with_relevance = keyword_builder is not None
    query = _pending_query(senta, with_relevance)

    def _updates(sentiment: Dict[str, Any], relevant: bool) -> Dict[str, Any]:
        fields = {"sentiment": sentiment}
        if with_relevance:
            fields["relevance"] = "on_topic" if relevant else "off_topic"
        return fields

    processed = 0
    alerts_created = 0
    offtopic = 0
    while processed < max_docs:
        cursor = coll.find(query).sort("collected_at", -1).limit(batch_size)
        docs: List[Dict[str, Any]] = [d async for d in cursor]
        if not docs:
            break

        texts = [text_builder(d) for d in docs]
        valid = [i for i, t in enumerate(texts) if t.strip()]
        valid_set = set(valid)

        # 空文本统一标（中性, 相关），推进游标避免死循环
        for i, doc in enumerate(docs):
            if i not in valid_set:
                await coll.update_one(
                    {id_field: doc[id_field]}, {"$set": _updates(neutral, True)}
                )

        if valid:
            # LLM 客户端是同步阻塞的，必须丢线程池，否则会卡死整个事件循环
            # （表现为分析期间所有 API 请求挂起数秒）
            if with_relevance:
                pairs = await asyncio.to_thread(
                    senta.batch_analyze_notes,
                    [texts[i] for i in valid],
                    [keyword_builder(docs[i]) for i in valid],
                )
            else:
                results = await asyncio.to_thread(
                    senta.batch_analyze, [texts[i] for i in valid]
                )
                pairs = [(r, True) for r in results]

            batch_alerts = []
            for i, (result, relevant) in zip(valid, pairs):
                doc = docs[i]
                # 无监控词的笔记不做相关性否决（无从判起）
                if with_relevance and not keyword_builder(doc):
                    relevant = True
                sdoc = (
                    result.model_dump()
                    if hasattr(result, "model_dump")
                    else result.dict()
                )
                await coll.update_one(
                    {id_field: doc[id_field]}, {"$set": _updates(sdoc, relevant)}
                )
                if not relevant:
                    offtopic += 1
                    continue
                if "sentiment" in doc:
                    continue  # 存量回填 relevance，不重复广播/告警
                if broadcast is not None:
                    await broadcast(doc, sdoc)
                alert = alert_eval({**doc, "sentiment": sdoc})
                if alert is not None:
                    batch_alerts.append(alert)
            if batch_alerts:
                alerts_created += await alert_service.emit(batch_alerts)

        processed += len(docs)

    if processed:
        logger.info(
            "%s 情感分析：本轮处理 %d 条，判偏题 %d 条，触发告警 %d 条",
            collection_name, processed, offtopic, alerts_created,
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
async def start_scheduler() -> None:
    """启动调度：每天北京时间 DAILY_COLLECT_HOUR 点跑一次采集+分析+告警。

    分析/告警串在 ``daily_collect`` 里，不再单独周期跑（评论采集已关停）。
    """
    scheduler.add_job(
        daily_collect,
        trigger=CronTrigger(
            hour=settings.DAILY_COLLECT_HOUR, minute=0, timezone="Asia/Shanghai"
        ),
        id="collect_keywords",
        name="每日采集+分析",
        replace_existing=True,
    )

    # 启动补采：机器错过了今天的采集点（如 8 点没开机）且今天没采过，立即补一次
    if await _needs_catchup():
        logger.info("检测到今天尚未采集，启动后补采一次")
        scheduler.add_job(
            daily_collect,
            id="collect_catchup",
            name="启动补采",
            next_run_time=datetime.utcnow() + timedelta(seconds=20),
        )

    scheduler.start()
    logger.info(
        "任务调度器已启动：每天北京时间 %d:00 采集", settings.DAILY_COLLECT_HOUR
    )


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("任务调度器已停止")
