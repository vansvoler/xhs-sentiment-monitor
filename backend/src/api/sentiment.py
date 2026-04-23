"""
情感分析 API 路由
"""
from fastapi import APIRouter
from src.models.sentiment import BatchSentimentRequest, BatchSentimentResponse
from src.analyzers.senta_service import get_sentiment_service
import time

router = APIRouter()


@router.post("/analyze", response_model=BatchSentimentResponse)
async def analyze_sentiment(request: BatchSentimentRequest):
    """
    批量分析文本情感
    
    - texts: 待分析文本列表
    """
    senta_service = get_sentiment_service()
    
    start_time = time.time()
    results = senta_service.batch_analyze(request.texts)
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
    
    # 笔记情感统计
    note_pipeline = [
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
