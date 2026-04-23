"""
趋势分析 API 路由
"""
from fastapi import APIRouter, Query
from src.services.trend_analysis import trend_analyzer

router = APIRouter()


@router.get("/daily")
async def get_daily_trend():
    """获取今日趋势"""
    trend = await trend_analyzer.analyze_daily_trend()
    return trend


@router.get("/series")
async def get_trend_series(days: int = Query(7, ge=1, le=30)):
    """
    获取趋势序列
    
    - days: 天数
    """
    trends = await trend_analyzer.get_trend_series(days)
    return trends


@router.get("/hot-topics")
async def get_hot_topics(
    limit: int = Query(10, ge=1, le=50),
    hours: int = Query(24, ge=1, le=168)
):
    """
    获取热门话题
    
    - limit: 返回数量
    - hours: 时间窗口（小时）
    """
    topics = await trend_analyzer.get_hot_topics(limit, hours)
    return topics
