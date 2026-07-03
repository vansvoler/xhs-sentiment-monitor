from datetime import datetime, timezone

import pytest

from src.models.intel import (
    IntelItem,
    IntelSourceSyncStatus,
    IntelSourceType,
)
from src.models.note import AuthorInfo, Note, NoteType, StatsInfo
from src.services import intel_feed
from src.services.intel_feed import (
    build_helper_rail,
    build_overview_feed,
    build_overview_sections,
    load_live_source_items,
    load_live_source_sync_reports,
    note_to_intel_item,
)


def make_item(source_type: IntelSourceType, source_name: str, title: str) -> IntelItem:
    return IntelItem(
        item_id=f"{source_type.value}-{title}",
        source_type=source_type,
        source_name=source_name,
        title=title,
        summary_short=f"{title} short",
        summary_long=f"{title} long",
        impact_targets=["本科"],
        published_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 5, 19, 8, 30, tzinfo=timezone.utc),
        original_url=f"https://example.com/{title}",
    )


def test_build_overview_sections_groups_by_source_type():
    items = [
        make_item(IntelSourceType.XIAOHONGSHU, "小红书", "xhs-1"),
        make_item(IntelSourceType.UCAS, "UCAS", "ucas-1"),
    ]

    sections = build_overview_sections(items)

    assert [section.source_key for section in sections] == [
        "ucas",
        "university_site",
        "exam_board",
        "visa_policy",
        "wechat_media",
    ]
    assert sections[0].total_items == 1
    assert all(section.source_key != "xiaohongshu" for section in sections)


def test_build_overview_sections_limits_preview_count():
    items = [make_item(IntelSourceType.UCAS, "UCAS", f"ucas-{idx}") for idx in range(5)]

    sections = build_overview_sections(items)
    ucas_section = next(section for section in sections if section.source_key == "ucas")

    assert len(ucas_section.preview_items) == 3


def test_build_helper_rail_counts_impact_targets():
    items = [
        make_item(IntelSourceType.UCAS, "UCAS", "ucas-1"),
        make_item(IntelSourceType.UCAS, "UCAS", "ucas-2").model_copy(
            update={"impact_targets": ["硕士", "申请季"]}
        ),
    ]

    rail = build_helper_rail(items)

    assert rail.highlight_count == 2
    assert rail.top_counts["本科"] == 1
    assert rail.top_counts["硕士"] == 1


def test_note_to_intel_item_maps_note_fields():
    note = Note(
        note_id="xhs-1",
        title="英国本科申请经验",
        content="分享申请过程中的时间节点和材料准备。",
        type=NoteType.NORMAL,
        author=AuthorInfo(user_id="u1", nickname="作者", fans_count=1),
        stats=StatsInfo(),
        published_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 5, 19, 8, 30, tzinfo=timezone.utc),
        keywords=["英国本科"],
        category="brand",
    )

    item = note_to_intel_item(note)

    assert item.source_type == IntelSourceType.XIAOHONGSHU
    assert item.source_name == "小红书"
    assert item.title == note.title
    assert item.summary_short.startswith("分享申请过程")
    assert "本科" in item.impact_targets
    assert item.original_url.endswith(note.note_id)


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    async def to_list(self, length=None):
        return self.rows[:length]


class _FakeCollection:
    def __init__(self, rows):
        self.rows = rows

    def find(self, *_args, **_kwargs):
        return _FakeCursor(self.rows)


@pytest.mark.asyncio
async def test_load_xiaohongshu_items_reads_note_collection(monkeypatch):
    row = {
        "note_id": "abc123",
        "title": "英国硕士签证材料",
        "content": "整理硕士签证流程与材料。",
        "type": "normal",
        "author": {"user_id": "u1", "nickname": "作者", "fans_count": 10},
        "stats": {"likes": 1, "comments": 2, "shares": 3, "collects": 4},
        "published_at": datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc),
        "collected_at": datetime(2026, 5, 19, 8, 30, tzinfo=timezone.utc),
        "keywords": ["硕士", "签证"],
        "category": "brand",
    }

    monkeypatch.setattr(
        intel_feed.mongodb,
        "get_collection",
        lambda name: _FakeCollection([row]),
    )

    items = await intel_feed.load_xiaohongshu_items(limit=5)

    assert len(items) == 1
    assert items[0].source_type == IntelSourceType.XIAOHONGSHU
    assert "硕士" in items[0].impact_targets


@pytest.mark.asyncio
async def test_load_live_source_items_reads_intel_collection(monkeypatch):
    row = {
        "item_id": "oxford-news:https://example.com/story",
        "source_type": "university_site",
        "source_name": "Oxford News",
        "title": "Oxford story",
        "summary_short": "Oxford story",
        "summary_long": "Oxford story",
        "impact_targets": [],
        "published_at": "2026-05-21T08:00:00Z",
        "collected_at": "2026-05-21T08:05:00Z",
        "original_url": "https://example.com/story",
        "school_name": "Oxford",
        "source_group": "重点学校",
    }

    monkeypatch.setattr(
        intel_feed.mongodb,
        "get_collection",
        lambda _name: _FakeCollection([row]),
    )

    items = await load_live_source_items("university_site", limit=10)

    assert len(items) == 1
    assert items[0].school_name == "Oxford"
    assert items[0].source_type == IntelSourceType.UNIVERSITY_SITE


@pytest.mark.asyncio
async def test_load_live_source_sync_reports_reads_sync_collection(monkeypatch):
    row = {
        "source_id": "oxford-news",
        "source_type": "university_site",
        "source_name": "Oxford News",
        "school_name": "Oxford",
        "status": "blocked",
        "item_count": 0,
        "error_message": "Cloudflare challenge",
        "synced_at": "2026-05-21T08:05:00Z",
    }

    monkeypatch.setattr(
        intel_feed.mongodb,
        "get_collection",
        lambda _name: _FakeCollection([row]),
    )

    reports = await load_live_source_sync_reports("university_site")

    assert len(reports) == 1
    assert reports[0].source_id == "oxford-news"
    assert reports[0].status == IntelSourceSyncStatus.BLOCKED


@pytest.mark.asyncio
async def test_build_overview_feed_prefers_live_university_items(monkeypatch, tmp_path):
    async def fake_live_items(_source_key: str, limit: int = 20):
        return [
            make_item(
                IntelSourceType.UNIVERSITY_SITE,
                "Oxford News",
                "Oxford live item",
            ).model_copy(
                update={
                    "school_name": "Oxford",
                    "source_group": "重点学校",
                }
            )
        ]

    monkeypatch.setattr(intel_feed, "load_live_source_items", fake_live_items)

    seed_path = tmp_path / "intel_seed.json"
    seed_path.write_text(
        """
        [
          {
            "item_id": "university_site-fixture",
            "source_type": "university_site",
            "source_name": "Fixture University",
            "title": "Fixture university item",
            "summary_short": "Fixture university item",
            "summary_long": "Fixture university item",
            "impact_targets": [],
            "published_at": "2026-05-19T08:00:00Z",
            "collected_at": "2026-05-19T08:30:00Z",
            "original_url": "https://example.com/fixture"
          }
        ]
        """,
        encoding="utf-8",
    )

    items = await build_overview_feed(seed_path)

    assert items[0].title == "Oxford live item"


@pytest.mark.asyncio
async def test_build_overview_feed_ignores_xiaohongshu_items(monkeypatch, tmp_path):
    async def fake_live_items(_source_key: str, limit: int = 20):
        return []

    monkeypatch.setattr(intel_feed, "load_live_source_items", fake_live_items)

    seed_path = tmp_path / "intel_seed.json"
    seed_path.write_text(
        """
        [
          {
            "item_id": "xhs-fixture",
            "source_type": "xiaohongshu",
            "source_name": "小红书",
            "title": "XHS fixture item",
            "summary_short": "XHS fixture item",
            "summary_long": "XHS fixture item",
            "impact_targets": [],
            "published_at": "2026-05-19T08:00:00Z",
            "collected_at": "2026-05-19T08:30:00Z",
            "original_url": "https://example.com/xhs"
          },
          {
            "item_id": "ucas-fixture",
            "source_type": "ucas",
            "source_name": "UCAS",
            "title": "UCAS fixture item",
            "summary_short": "UCAS fixture item",
            "summary_long": "UCAS fixture item",
            "impact_targets": [],
            "published_at": "2026-05-19T08:00:00Z",
            "collected_at": "2026-05-19T08:30:00Z",
            "original_url": "https://example.com/ucas"
          }
        ]
        """,
        encoding="utf-8",
    )

    items = await build_overview_feed(seed_path)

    assert [item.source_type for item in items] == [IntelSourceType.UCAS]


@pytest.mark.asyncio
async def test_build_overview_feed_prefers_live_ucas_items(monkeypatch, tmp_path):
    async def fake_live_items(source_key: str, limit: int = 20):
        if source_key == IntelSourceType.UCAS.value:
            return [
                make_item(
                    IntelSourceType.UCAS,
                    "UCAS",
                    "UCAS live item",
                )
            ]
        return []

    monkeypatch.setattr(intel_feed, "load_live_source_items", fake_live_items)

    seed_path = tmp_path / "intel_seed.json"
    seed_path.write_text(
        """
        [
          {
            "item_id": "ucas-fixture",
            "source_type": "ucas",
            "source_name": "UCAS",
            "title": "Fixture UCAS item",
            "summary_short": "Fixture UCAS item",
            "summary_long": "Fixture UCAS item",
            "impact_targets": [],
            "published_at": "2026-05-19T08:00:00Z",
            "collected_at": "2026-05-19T08:30:00Z",
            "original_url": "https://example.com/fixture"
          }
        ]
        """,
        encoding="utf-8",
    )

    items = await build_overview_feed(seed_path)

    assert any(item.title == "UCAS live item" for item in items)
    assert not any(item.title == "Fixture UCAS item" for item in items)


@pytest.mark.asyncio
async def test_build_overview_feed_includes_live_policy_sources(monkeypatch, tmp_path):
    async def fake_live_items(source_key: str, limit: int = 20):
        if source_key == IntelSourceType.VISA_POLICY.value:
            return [
                make_item(
                    IntelSourceType.VISA_POLICY,
                    "UKVI News",
                    "Student visa live item",
                )
            ]
        return []

    monkeypatch.setattr(intel_feed, "load_live_source_items", fake_live_items)

    seed_path = tmp_path / "intel_seed.json"
    seed_path.write_text("[]", encoding="utf-8")

    items = await build_overview_feed(seed_path)

    assert [item.title for item in items] == ["Student visa live item"]
