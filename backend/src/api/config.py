"""
配置读取 API
"""
from fastapi import APIRouter
from src.config import settings

router = APIRouter()


@router.get("/keywords")
async def get_keywords():
    """返回监控关键词分组，供前端 Header 展示关键词标签"""
    return {
        "brand": settings.MONITOR_KEYWORDS_BRAND,
        "competitor": settings.MONITOR_KEYWORDS_COMPETITOR,
        "industry": settings.MONITOR_KEYWORDS_INDUSTRY,
        "all": settings.all_keywords,
    }
