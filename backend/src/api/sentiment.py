"""
情感分析 API 路由（含负面舆情工作台）
"""
import asyncio
import time
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from src.analyzers.sentiment_service import get_sentiment_service
from src.models.sentiment import (
    BatchSentimentRequest,
    BatchSentimentResponse,
    NegativeItem,
    NegativeStatusRequest,
)
from src.services.negative_feed import negative_feed

router = APIRouter()

Kind = Literal["note", "comment"]


@router.post("/analyze", response_model=BatchSentimentResponse)
async def analyze_sentiment(request: BatchSentimentRequest):
    """
    批量分析文本情感
    
    - texts: 待分析文本列表
    """
    service = get_sentiment_service()

    start_time = time.time()
    # 同步 LLM 调用丢线程池，避免阻塞事件循环
    results = await asyncio.to_thread(service.batch_analyze, request.texts)
    processing_time = time.time() - start_time

    return BatchSentimentResponse(
        results=results,
        total=len(results),
        processing_time=processing_time
    )


@router.get("/stats")
async def get_sentiment_stats():
    """获取情感统计"""
    from src.db.mongodb import mongodb

    notes_collection = mongodb.get_collection("notes")
    comments_collection = mongodb.get_collection("comments")

    from src.db.filters import ON_TOPIC

    # 笔记情感统计（排除语义偏题）
    note_pipeline = [
        {"$match": ON_TOPIC},
        {"$group": {
            "_id": "$sentiment.label",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$sentiment.score"}
        }}
    ]
    note_stats = await notes_collection.aggregate(note_pipeline).to_list(length=None)

    # 评论情感统计
    comment_pipeline = [
        {"$group": {
            "_id": "$sentiment.label",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$sentiment.score"}
        }}
    ]
    comment_stats = await comments_collection.aggregate(comment_pipeline).to_list(length=None)

    return {
        "notes": {
            item["_id"]: {"count": item["count"], "avg_score": item["avg_score"]}
            for item in note_stats
        },
        "comments": {
            item["_id"]: {"count": item["count"], "avg_score": item["avg_score"]}
            for item in comment_stats
        }
    }


# ================ 负面舆情工作台 ================
@router.get("/negative", response_model=List[NegativeItem])
async def list_negative(  # noqa: PLR0913
    kind: Kind = "note",
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    status: Literal["open", "handled", "all"] = "open",
    sort: Literal["influence", "latest"] = "influence",
):
    """负面笔记/评论统一列表（默认只看未处置、按影响力排序）"""
    return await negative_feed.list_items(
        kind, skip=skip, limit=limit, category=category,
        keyword=keyword, status=status, sort=sort,
    )


@router.get("/negative/summary")
async def negative_summary():
    """未处置负面内容计数（徽标）"""
    return await negative_feed.summary()


@router.post("/negative/{kind}/{item_id}/status")
async def set_negative_status(kind: Kind, item_id: str, req: NegativeStatusRequest):
    """标记负面条目处置状态（open / handled）"""
    if req.status not in ("open", "handled"):
        raise HTTPException(status_code=422, detail="status 必须是 open 或 handled")
    if not await negative_feed.set_status(kind, item_id, req.status):
        raise HTTPException(status_code=404, detail="条目不存在")
    return {"ok": True}
