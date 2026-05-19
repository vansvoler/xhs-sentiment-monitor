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


@router.get("/source-nav")
async def get_source_nav():
    """返回运营工作台来源导航元信息"""
    return {
        "items": [
            {"key": "overview", "label": "总览"},
            {"key": "xiaohongshu", "label": "小红书"},
            {"key": "ucas", "label": "UCAS"},
            {"key": "university_site", "label": "海外大学官网"},
            {"key": "wechat_media", "label": "媒体公众号"},
        ]
    }
