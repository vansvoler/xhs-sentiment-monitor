"""
统一运营情报 feed helper
"""
from collections import Counter
from collections.abc import Iterable

from src.models.intel import (
    IntelHelperRail,
    IntelItem,
    IntelOverviewSection,
    IntelSourceType,
)

SOURCE_LABELS = {
    IntelSourceType.XIAOHONGSHU: "小红书",
    IntelSourceType.UCAS: "UCAS",
    IntelSourceType.UNIVERSITY_SITE: "海外大学官网",
    IntelSourceType.WECHAT_MEDIA: "媒体公众号",
}


def build_overview_sections(items: Iterable[IntelItem]) -> list[IntelOverviewSection]:
    """按来源构建总览页分区"""

    grouped: dict[IntelSourceType, list[IntelItem]] = {}
    for item in items:
        grouped.setdefault(item.source_type, []).append(item)

    sections: list[IntelOverviewSection] = []
    for source_type, source_label in SOURCE_LABELS.items():
        source_items = grouped.get(source_type, [])
        sections.append(
            IntelOverviewSection(
                source_key=source_type.value,
                source_label=source_label,
                total_items=len(source_items),
                preview_items=source_items[:3],
            )
        )

    return sections


def build_helper_rail(items: Iterable[IntelItem]) -> IntelHelperRail:
    """统计右侧轻辅助栏"""

    counter: Counter[str] = Counter()
    item_list = list(items)

    for item in item_list:
        counter.update(item.impact_targets)

    return IntelHelperRail(
        highlight_count=min(3, len(item_list)),
        top_counts=dict(counter.most_common(5)),
    )
