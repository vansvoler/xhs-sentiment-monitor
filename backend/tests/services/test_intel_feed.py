from datetime import datetime, timezone

from src.models.intel import IntelItem, IntelSourceType
from src.models.note import AuthorInfo, Note, NoteType, StatsInfo
from src.services import intel_feed
from src.services.intel_feed import (
    build_helper_rail,
    build_overview_sections,
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
        "xiaohongshu",
        "ucas",
        "university_site",
        "wechat_media",
    ]
    assert sections[0].total_items == 1
    assert sections[1].total_items == 1


def test_build_overview_sections_limits_preview_count():
    items = [make_item(IntelSourceType.UCAS, "UCAS", f"ucas-{idx}") for idx in range(5)]

    sections = build_overview_sections(items)

    assert len(sections[1].preview_items) == 3


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


import pytest


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
