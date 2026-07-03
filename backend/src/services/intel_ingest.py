"""运营情报统一入库服务。"""

from collections.abc import Iterable
from datetime import datetime, timezone

import aiohttp

from src.collectors.ucas_news import collect_ucas_news_with_report
from src.collectors.university_news import (
    SourceBlockedError,
    collect_all_university_news_with_reports,
    collect_source_items,
)
from src.collectors.university_sources import IntelSource, load_intel_sources
from src.db.mongodb import close_mongodb, init_mongodb, mongodb
from src.models.intel import IntelItem, IntelSourceSyncReport, IntelSourceSyncStatus


async def upsert_intel_items(collection, items: Iterable[IntelItem]) -> int:
    """把统一情报项 upsert 到 MongoDB。"""

    count = 0
    for item in items:
        await collection.update_one(
            {"item_id": item.item_id},
            {"$set": item.model_dump(mode="json")},
            upsert=True,
        )
        count += 1

    return count


async def persist_intel_items(items: Iterable[IntelItem]) -> int:
    """写入默认 `intel_items` 集合。"""

    collection = mongodb.get_collection("intel_items")
    return await upsert_intel_items(collection, items)


async def upsert_source_sync_reports(
    collection,
    reports: Iterable[IntelSourceSyncReport],
) -> int:
    """把来源同步结果 upsert 到 MongoDB。"""

    count = 0
    for report in reports:
        await collection.update_one(
            {"source_id": report.source_id},
            {"$set": report.model_dump(mode="json")},
            upsert=True,
        )
        count += 1

    return count


async def persist_source_sync_reports(
    reports: Iterable[IntelSourceSyncReport],
) -> int:
    """写入默认 `intel_source_syncs` 集合。"""

    collection = mongodb.get_collection("intel_source_syncs")
    return await upsert_source_sync_reports(collection, reports)


async def collect_university_news_with_reports(
    sources: list[IntelSource] | None = None,
) -> tuple[list[IntelItem], list[IntelSourceSyncReport]]:
    """抓取全部大学新闻信源及逐来源报告。

    ``sources`` 缺省时从 ``intel_sources.json`` 重新加载，使得通过 API 动态新增的
    信源在下一次调度时立即被纳入抓取范围（无需重启进程）。
    """

    effective_sources = sources if sources is not None else load_intel_sources()

    async with aiohttp.ClientSession() as session:
        return await collect_all_university_news_with_reports(
            session,
            effective_sources,
        )


async def sync_university_news(
    sources: list[IntelSource] | None = None,
) -> int:
    """抓取并写入大学新闻情报。"""

    items, reports = await collect_university_news_with_reports(sources)
    await persist_source_sync_reports(reports)

    if not items:
        return 0

    return await persist_intel_items(items)


async def sync_intel_source(source: IntelSource) -> tuple[int, IntelSourceSyncReport]:
    """抓取并写入单个官网/机构信源。"""

    synced_at = datetime.now(timezone.utc)

    async with aiohttp.ClientSession() as session:
        try:
            items = await collect_source_items(session, source)
        except SourceBlockedError as exc:
            report = IntelSourceSyncReport(
                source_id=source.source_id,
                source_type=source.source_type,
                source_name=source.source_name,
                school_name=source.school_name,
                status=IntelSourceSyncStatus.BLOCKED,
                error_message=str(exc),
                synced_at=synced_at,
            )
            await persist_source_sync_reports([report])
            return 0, report
        except Exception as exc:
            report = IntelSourceSyncReport(
                source_id=source.source_id,
                source_type=source.source_type,
                source_name=source.source_name,
                school_name=source.school_name,
                status=IntelSourceSyncStatus.ERROR,
                error_message=str(exc),
                synced_at=synced_at,
            )
            await persist_source_sync_reports([report])
            return 0, report

    report = IntelSourceSyncReport(
        source_id=source.source_id,
        source_type=source.source_type,
        source_name=source.source_name,
        school_name=source.school_name,
        status=IntelSourceSyncStatus.SUCCESS,
        item_count=len(items),
        synced_at=synced_at,
    )
    await persist_source_sync_reports([report])

    if not items:
        return 0, report

    return await persist_intel_items(items), report


async def collect_ucas_news_job() -> tuple[list[IntelItem], IntelSourceSyncReport]:
    """抓取 UCAS 新闻情报及同步结果。"""

    async with aiohttp.ClientSession() as session:
        return await collect_ucas_news_with_report(session)


async def sync_ucas_news() -> int:
    """抓取并写入 UCAS 情报。"""

    items, report = await collect_ucas_news_job()
    await persist_source_sync_reports([report])

    if not items:
        return 0

    return await persist_intel_items(items)


async def run_university_news_sync_job() -> int:
    """运行独立大学新闻同步任务并管理数据库生命周期。"""

    await init_mongodb()
    try:
        return await sync_university_news()
    finally:
        await close_mongodb()


async def run_ucas_news_sync_job() -> int:
    """运行独立 UCAS 同步任务并管理数据库生命周期。"""

    await init_mongodb()
    try:
        return await sync_ucas_news()
    finally:
        await close_mongodb()
