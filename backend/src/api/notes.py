"""
笔记 API 路由
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.db.filters import ON_TOPIC
from src.db.mongodb import mongodb
from src.models.note import Note

router = APIRouter()


@router.get("/", response_model=List[Note])
async def list_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    sentiment: Optional[str] = None,
    keyword: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    获取笔记列表

    - skip: 跳过数量
    - limit: 返回数量
    - category: 分类筛选
    - sentiment: 情感筛选（positive / negative / neutral）
    - keyword: 监控词筛选（匹配 search_keyword）
    - start_date: 开始时间
    - end_date: 结束时间
    """
    collection = mongodb.get_collection("notes")

    query: Dict[str, Any] = {**ON_TOPIC}
    if category:
        query["category"] = category
    if sentiment:
        query["sentiment.label"] = sentiment
    if keyword:
        query["search_keyword"] = keyword
    if start_date or end_date:
        date_range: Dict[str, Any] = {}
        if start_date:
            date_range["$gte"] = start_date
        if end_date:
            date_range["$lt"] = end_date
        query["collected_at"] = date_range

    # 按发布时间排序：舆情时间轴统一用 published_at（与趋势/竞品/告警一致）
    cursor = collection.find(query).skip(skip).limit(limit).sort("published_at", -1)
    notes = await cursor.to_list(length=limit)

    return notes


@router.get("/{note_id}", response_model=Note)
async def get_note(note_id: str):
    """获取笔记详情"""
    collection = mongodb.get_collection("notes")
    note = await collection.find_one({"note_id": note_id})

    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    return note


@router.get("/stats/summary")
async def get_notes_summary(category: Optional[str] = None):
    """获取笔记统计摘要，支持按 category 过滤"""
    notes_collection = mongodb.get_collection("notes")

    base_query: dict = {**ON_TOPIC}
    if category:
        base_query["category"] = category

    total_notes = await notes_collection.count_documents(base_query)

    # "今日"按北京时间零点算（库内时间为朴素 UTC，转回 UTC 再比较）
    cst = timezone(timedelta(hours=8))
    today_cst = datetime.now(cst).replace(hour=0, minute=0, second=0, microsecond=0)
    today = today_cst.astimezone(timezone.utc).replace(tzinfo=None)
    today_notes = await notes_collection.count_documents(
        {**base_query, "collected_at": {"$gte": today}}
    )

    # 情感分布
    pipeline = [
        *(
            [{"$match": base_query}] if base_query else []
        ),
        {"$group": {
            "_id": "$sentiment.label",
            "count": {"$sum": 1}
        }}
    ]
    sentiment_stats = await notes_collection.aggregate(pipeline).to_list(length=None)

    sentiment_distribution = {
        item["_id"]: item["count"]
        for item in sentiment_stats
    }

    return {
        "total_notes": total_notes,
        "today_notes": today_notes,
        "sentiment_distribution": sentiment_distribution
    }
