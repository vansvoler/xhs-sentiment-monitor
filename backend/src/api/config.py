"""
配置读写 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.keyword_config import keyword_config

router = APIRouter()


@router.get("/keywords")
async def get_keywords():
    """返回监控关键词分组 {brand, competitor, industry, all}"""
    return await keyword_config.list_grouped()


class KeywordBody(BaseModel):
    keyword: str
    category: str  # brand / competitor / industry


@router.post("/keywords")
async def add_keyword(body: KeywordBody):
    """新增监控关键词，返回更新后的分组"""
    try:
        await keyword_config.add(body.keyword, body.category)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return await keyword_config.list_grouped()


@router.delete("/keywords/{keyword}")
async def remove_keyword(keyword: str):
    """删除监控关键词，返回更新后的分组"""
    if not await keyword_config.remove(keyword):
        raise HTTPException(status_code=404, detail="关键词不存在")
    return await keyword_config.list_grouped()


@router.get("/source-nav")
async def get_source_nav():
    """返回运营工作台来源导航元信息"""
    return {
        "items": [
            {"key": "overview", "label": "总览"},
            {"key": "ucas", "label": "UCAS"},
            {"key": "university_site", "label": "海外大学官网"},
            {"key": "exam_board", "label": "考试局"},
            {"key": "visa_policy", "label": "签证政策"},
            {"key": "wechat_media", "label": "媒体公众号"},
        ]
    }
