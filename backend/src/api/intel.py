"""
运营情报聚合 API
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.services.intel_feed import (
    build_helper_rail,
    build_overview_sections,
    build_source_feed,
    load_fixture_items,
)

router = APIRouter()

SEED_PATH = Path(__file__).resolve().parents[2] / "temp" / "intel_seed.json"
VALID_SOURCE_KEYS = {"xiaohongshu", "ucas", "university_site", "wechat_media"}


@router.get("/overview")
async def get_intel_overview():
    """返回总览页来源分区和右侧辅助栏"""

    items = load_fixture_items(SEED_PATH)
    return {
        "sections": [section.model_dump(mode="json") for section in build_overview_sections(items)],
        "helper_rail": build_helper_rail(items).model_dump(mode="json"),
    }


@router.get("/sources/{source_key}")
async def get_source_feed(source_key: str):
    """返回来源详情页数据"""

    if source_key not in VALID_SOURCE_KEYS:
        raise HTTPException(status_code=404, detail="来源不存在")

    items = load_fixture_items(SEED_PATH)
    source_items = build_source_feed(items, source_key)

    return {
        "source_key": source_key,
        "items": [item.model_dump(mode="json") for item in source_items],
        "helper_rail": build_helper_rail(source_items).model_dump(mode="json"),
    }
