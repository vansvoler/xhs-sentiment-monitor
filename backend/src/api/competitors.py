"""
竞品分析 API 路由
"""
from fastapi import APIRouter, Query
from typing import List
from src.services.competitor_monitor import competitor_monitor
from src.models.note import CompetitorData

router = APIRouter()


@router.get("/compare", response_model=List[CompetitorData])
async def compare_competitors(
    names: str = Query(None),
    days: int = Query(30, ge=1, le=90)
):
    """
    比较竞品
    
    - names: 竞品名称列表，逗号分隔
    - days: 分析天数
    """
    competitor_list = names.split(",") if names else None
    results = await competitor_monitor.compare_competitors(competitor_list, days)
    return results


@router.get("/{name}")
async def get_competitor_data(
    name: str,
    days: int = Query(30, ge=1, le=90)
):
    """
    获取竞品详情
    
    - name: 竞品名称
    - days: 分析天数
    """
    data = await competitor_monitor.analyze_competitor(name, days)
    return data


@router.get("/{name}/trends")
async def get_competitor_trends(
    name: str,
    days: int = Query(30, ge=1, le=90)
):
    """
    获取竞品趋势
    
    - name: 竞品名称
    - days: 分析天数
    """
    trends = await competitor_monitor.get_competitor_trends(name, days)
    return trends
