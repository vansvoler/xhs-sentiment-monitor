from datetime import datetime, timezone

import pytest

from src.collectors.university_sources import IntelSource
from src.models.intel import (
    IntelItem,
    IntelSourceSyncReport,
    IntelSourceSyncStatus,
    IntelSourceType,
)
from src.services import intel_ingest
from src.services.intel_ingest import (
    run_ucas_news_sync_job,
    run_university_news_sync_job,
    sync_intel_source,
    sync_ucas_news,
    sync_university_news,
    upsert_intel_items,
    upsert_source_sync_reports,
)


class _FakeCollection:
    def __init__(self) -> None:
        self.calls = []

    async def update_one(self, query, update, upsert):
        self.calls.append((query, update, upsert))


@pytest.mark.asyncio
async def test_upsert_intel_items_uses_item_id_as_key():
    collection = _FakeCollection()
    items = [
        IntelItem(
            item_id="cambridge-news:https://example.com/story",
            source_type=IntelSourceType.UNIVERSITY_SITE,
            source_name="Cambridge News",
            title="Story",
            summary_short="Story",
            summary_long="Story",
            published_at=datetime(2026, 5, 21, 8, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 5, 21, 8, 5, tzinfo=timezone.utc),
            original_url="https://example.com/story",
            school_name="Cambridge",
            source_group="重点学校",
        )
    ]

    count = await upsert_intel_items(collection, items)

    assert count == 1
    assert collection.calls[0][0] == {"item_id": items[0].item_id}
    assert collection.calls[0][2] is True


@pytest.mark.asyncio
async def test_upsert_source_sync_reports_uses_source_id_as_key():
    collection = _FakeCollection()
    reports = [
        IntelSourceSyncReport(
            source_id="oxford-news",
            source_type=IntelSourceType.UNIVERSITY_SITE,
            source_name="Oxford News",
            school_name="Oxford",
            status=IntelSourceSyncStatus.BLOCKED,
            error_message="Cloudflare challenge",
            synced_at=datetime(2026, 5, 21, 8, 5, tzinfo=timezone.utc),
        )
    ]

    count = await upsert_source_sync_reports(collection, reports)

    assert count == 1
    assert collection.calls[0][0] == {"source_id": "oxford-news"}


@pytest.mark.asyncio
async def test_sync_university_news_collects_and_persists(monkeypatch):
    items = [
        IntelItem(
            item_id="oxford-news:https://example.com/story",
            source_type=IntelSourceType.UNIVERSITY_SITE,
            source_name="Oxford News",
            title="Story",
            summary_short="Story",
            summary_long="Story",
            published_at=datetime(2026, 5, 21, 8, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 5, 21, 8, 5, tzinfo=timezone.utc),
            original_url="https://example.com/story",
            school_name="Oxford",
            source_group="重点学校",
        )
    ]

    async def fake_collect(sources=None):
        return items, []

    async def fake_persist(collected_items):
        assert collected_items == items
        return len(collected_items)

    async def fake_persist_reports(reports):
        assert reports == []
        return 0

    monkeypatch.setattr(
        intel_ingest, "collect_university_news_with_reports", fake_collect
    )
    monkeypatch.setattr(intel_ingest, "persist_intel_items", fake_persist)
    monkeypatch.setattr(
        intel_ingest, "persist_source_sync_reports", fake_persist_reports
    )

    count = await sync_university_news()

    assert count == 1


@pytest.mark.asyncio
async def test_sync_university_news_uses_caller_supplied_sources(monkeypatch):
    """Phase A1：调用方传入的 sources 会被透传到底层抓取函数，不再依赖模块静态变量。"""

    sentinel = [
        IntelSource(
            source_id="dynamic-news",
            source_type=IntelSourceType.UNIVERSITY_SITE,
            source_name="Dynamic News",
            source_group="动态来源",
            adapter_type="feed",
            feed_url="https://example.com/dynamic.xml",
        )
    ]
    observed: dict[str, object] = {}

    async def fake_collect(sources=None):
        observed["sources"] = sources
        return [], []

    async def fake_persist_reports(reports):
        return 0

    monkeypatch.setattr(
        intel_ingest, "collect_university_news_with_reports", fake_collect
    )
    monkeypatch.setattr(
        intel_ingest, "persist_source_sync_reports", fake_persist_reports
    )

    await sync_university_news(sentinel)

    assert observed["sources"] is sentinel


@pytest.mark.asyncio
async def test_sync_intel_source_collects_single_source_and_persists(monkeypatch):
    source = IntelSource(
        source_id="cie-news",
        source_type=IntelSourceType.EXAM_BOARD,
        source_name="CIE",
        source_group="考试局",
        adapter_type="feed",
        feed_url="https://example.com/cie.xml",
    )
    items = [
        IntelItem(
            item_id="cie-news:https://example.com/story",
            source_type=IntelSourceType.EXAM_BOARD,
            source_name="CIE",
            title="CIE story",
            summary_short="CIE story",
            summary_long="CIE story",
            published_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 5, 28, 8, 5, tzinfo=timezone.utc),
            original_url="https://example.com/story",
            source_group="考试局",
        )
    ]
    events = []

    async def fake_collect(_session, configured_source):
        assert configured_source == source
        return items

    async def fake_persist(collected_items):
        events.append(("items", collected_items))
        return len(collected_items)

    async def fake_persist_reports(reports):
        events.append(("reports", reports))
        return len(reports)

    monkeypatch.setattr(intel_ingest, "collect_source_items", fake_collect)
    monkeypatch.setattr(intel_ingest, "persist_intel_items", fake_persist)
    monkeypatch.setattr(
        intel_ingest, "persist_source_sync_reports", fake_persist_reports
    )

    item_count, report = await sync_intel_source(source)

    assert item_count == 1
    assert report.source_id == "cie-news"
    assert report.source_type == IntelSourceType.EXAM_BOARD
    assert report.status == IntelSourceSyncStatus.SUCCESS
    assert report.item_count == 1
    assert events[0] == ("reports", [report])
    assert events[1] == ("items", items)


@pytest.mark.asyncio
async def test_run_university_news_sync_job_wraps_db_lifecycle(monkeypatch):
    events = []

    async def fake_init():
        events.append("init")

    async def fake_sync():
        events.append("sync")
        return 3

    async def fake_close():
        events.append("close")

    monkeypatch.setattr(intel_ingest, "init_mongodb", fake_init)
    monkeypatch.setattr(intel_ingest, "sync_university_news", fake_sync)
    monkeypatch.setattr(intel_ingest, "close_mongodb", fake_close)

    count = await run_university_news_sync_job()

    assert count == 3
    assert events == ["init", "sync", "close"]


@pytest.mark.asyncio
async def test_sync_ucas_news_collects_and_persists(monkeypatch):
    items = [
        IntelItem(
            item_id="ucas-news:https://www.ucas.com/example-story",
            source_type=IntelSourceType.UCAS,
            source_name="UCAS",
            title="UCAS story",
            summary_short="UCAS story",
            summary_long="UCAS story",
            published_at=datetime(2026, 5, 21, 8, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 5, 21, 8, 5, tzinfo=timezone.utc),
            original_url="https://www.ucas.com/example-story",
        )
    ]
    report = IntelSourceSyncReport(
        source_id="ucas-news",
        source_type=IntelSourceType.UCAS,
        source_name="UCAS",
        status=IntelSourceSyncStatus.SUCCESS,
        item_count=1,
        synced_at=datetime(2026, 5, 21, 8, 5, tzinfo=timezone.utc),
    )

    async def fake_collect():
        return items, report

    async def fake_persist(collected_items):
        assert collected_items == items
        return len(collected_items)

    async def fake_persist_reports(reports):
        assert reports == [report]
        return 1

    monkeypatch.setattr(intel_ingest, "collect_ucas_news_job", fake_collect)
    monkeypatch.setattr(intel_ingest, "persist_intel_items", fake_persist)
    monkeypatch.setattr(
        intel_ingest, "persist_source_sync_reports", fake_persist_reports
    )

    count = await sync_ucas_news()

    assert count == 1


@pytest.mark.asyncio
async def test_run_ucas_news_sync_job_wraps_db_lifecycle(monkeypatch):
    events = []

    async def fake_init():
        events.append("init")

    async def fake_sync():
        events.append("sync")
        return 2

    async def fake_close():
        events.append("close")

    monkeypatch.setattr(intel_ingest, "init_mongodb", fake_init)
    monkeypatch.setattr(intel_ingest, "sync_ucas_news", fake_sync)
    monkeypatch.setattr(intel_ingest, "close_mongodb", fake_close)

    count = await run_ucas_news_sync_job()

    assert count == 2
    assert events == ["init", "sync", "close"]
