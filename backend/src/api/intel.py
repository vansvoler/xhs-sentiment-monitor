"""
运营情报聚合 API
"""

from pathlib import Path

import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.collectors.intel_source_probe import probe_intel_source
from src.collectors.university_sources import CONFIG_PATH, IntelSource
from src.models.intel import IntelSourceType
from src.services.intel_feed import (
    build_helper_rail,
    build_overview_feed,
    build_overview_sections,
    build_source_feed,
    load_fixture_items,
    load_live_source_items,
    load_live_source_sync_reports,
)
from src.services.intel_ingest import sync_intel_source
from src.services.intel_source_config import (
    DuplicateIntelSourceError,
    append_intel_source,
)

router = APIRouter()

SEED_PATH = Path(__file__).resolve().parents[2] / "temp" / "intel_seed.json"
VALID_SOURCE_KEYS = {
    "ucas",
    "university_site",
    "exam_board",
    "visa_policy",
    "wechat_media",
}


class ProbeIntelSourceRequest(BaseModel):
    """前端信源探测请求。"""

    url: str
    source_type: IntelSourceType = IntelSourceType.UNIVERSITY_SITE
    source_name: str | None = None
    source_group: str = "自定义来源"


def _validate_source_config(source: IntelSource) -> None:
    """校验适配器必需字段。"""

    if source.adapter_type in {"feed", "rss", "json_feed"} and not source.feed_url:
        raise HTTPException(status_code=422, detail="feed 类型信源必须包含 feed_url")

    if source.adapter_type in {"listing", "html_listing"} and not source.listing_url:
        raise HTTPException(status_code=422, detail="列表页信源必须包含 listing_url")

    if source.adapter_type == "html_listing" and source.selectors is None:
        raise HTTPException(
            status_code=422,
            detail="html_listing 类型信源必须包含 selectors",
        )


@router.get("/overview")
async def get_intel_overview():
    """返回总览页来源分区和右侧辅助栏"""

    items = await build_overview_feed(SEED_PATH)
    return {
        "sections": [
            section.model_dump(mode="json")
            for section in build_overview_sections(items)
        ],
        "helper_rail": build_helper_rail(items).model_dump(mode="json"),
    }


@router.post("/sources/probe")
async def probe_source(request: ProbeIntelSourceRequest):
    """探测 URL 并返回推荐信源配置。"""

    async with aiohttp.ClientSession() as session:
        result = await probe_intel_source(
            session,
            request.url,
            source_type=request.source_type.value,
            source_name=request.source_name,
            source_group=request.source_group,
        )

    return {
        "status": result.status,
        "message": result.message,
        "sample_count": result.sample_count,
        "recommended_source": result.recommended_source.model_dump(mode="json"),
    }


@router.post("/sources", status_code=201)
async def create_source(source: IntelSource):
    """保存前端确认后的信源配置。"""

    _validate_source_config(source)

    try:
        saved_source = append_intel_source(CONFIG_PATH, source)
    except DuplicateIntelSourceError as exc:
        raise HTTPException(status_code=409, detail="信源已存在") from exc

    item_count, sync_report = await sync_intel_source(saved_source)

    return {
        "source": saved_source.model_dump(mode="json"),
        "item_count": item_count,
        "sync_report": sync_report.model_dump(mode="json"),
    }


@router.get("/sources/{source_key}")
async def get_source_feed(source_key: str):
    """返回来源详情页数据"""

    if source_key not in VALID_SOURCE_KEYS:
        raise HTTPException(status_code=404, detail="来源不存在")

    items = await load_live_source_items(source_key)

    sync_reports = await load_live_source_sync_reports(source_key)

    if not items:
        items = build_source_feed(load_fixture_items(SEED_PATH), source_key)

    return {
        "source_key": source_key,
        "items": [item.model_dump(mode="json") for item in items],
        "helper_rail": build_helper_rail(items).model_dump(mode="json"),
        "sync_reports": [report.model_dump(mode="json") for report in sync_reports],
    }


@router.get("/sources/{source_key}/sync-status")
async def get_source_sync_status(source_key: str):
    """返回来源同步状态。"""

    if source_key not in VALID_SOURCE_KEYS:
        raise HTTPException(status_code=404, detail="来源不存在")

    reports = await load_live_source_sync_reports(source_key)
    return {
        "source_key": source_key,
        "reports": [report.model_dump(mode="json") for report in reports],
    }
