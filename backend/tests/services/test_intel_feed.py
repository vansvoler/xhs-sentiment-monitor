from datetime import datetime, timezone

from src.models.intel import IntelItem, IntelSourceType
from src.services.intel_feed import build_helper_rail, build_overview_sections


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
