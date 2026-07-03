"""
趋势分析 API 路由
"""
from typing import Optional

from fastapi import APIRouter, Query

from src.services.trend_analysis import trend_analyzer

router = APIRouter()


@router.get("/daily")
async def get_daily_trend():
    """获取今日趋势"""
    trend = await trend_analyzer.analyze_daily_trend()
    return trend


@router.get("/series")
async def get_trend_series(
    days: int = Query(7, ge=1, le=400),
    category: Optional[str] = Query(None, description="brand/competitor/industry"),
):
    """
    获取趋势序列

    - days: 天数（上限 400，便于查看历史区间）
    - category: 按桶值过滤（brand/competitor/industry）
    """
    trends = await trend_analyzer.get_trend_series(days, category)
    return trends


@router.get("/hot-topics")
async def get_hot_topics(
    limit: int = Query(10, ge=1, le=50),
    hours: int = Query(24, ge=1, le=8760),
    category: Optional[str] = Query(None, description="brand/competitor/industry"),
):
    """
    获取热门话题

    - limit: 返回数量
    - hours: 时间窗口（小时，上限一年）
    - category: 按桶值过滤
    """
    topics = await trend_analyzer.get_hot_topics(limit, hours, category)
    return topics
