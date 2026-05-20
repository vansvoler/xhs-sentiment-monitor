"""
统一运营情报 feed helper
"""
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from src.db.mongodb import mongodb
from src.models.intel import (
    IntelHelperRail,
    IntelItem,
    IntelOverviewSection,
    IntelSourceType,
)
from src.models.note import Note
from src.services.intel_seed import load_seed_items

SOURCE_LABELS = {
    IntelSourceType.XIAOHONGSHU: "小红书",
    IntelSourceType.UCAS: "UCAS",
    IntelSourceType.UNIVERSITY_SITE: "海外大学官网",
    IntelSourceType.WECHAT_MEDIA: "媒体公众号",
}


def infer_impact_targets(title: str, content: str) -> list[str]:
    """从标题和正文中推断影响对象"""

    text = f"{title} {content}"
    targets: list[str] = []

    if "本科" in text:
        targets.append("本科")
    if "硕士" in text:
        targets.append("硕士")
    if "申请" in text or "时间线" in text:
        targets.append("申请季")
    if "签证" in text:
        targets.append("签证")
    if "奖学金" in text:
        targets.append("奖学金")

    return targets


def note_to_intel_item(note: Note) -> IntelItem:
    """把小红书 note 归一化成统一情报项"""

    content = note.content.strip()
    summary_short = content[:80] if content else note.title
    summary_long = content[:180] if content else note.title

    return IntelItem(
        item_id=f"xhs-{note.note_id}",
        source_type=IntelSourceType.XIAOHONGSHU,
        source_name="小红书",
        title=note.title,
        summary_short=summary_short,
        summary_long=summary_long,
        impact_targets=infer_impact_targets(note.title, note.content),
        published_at=note.published_at,
        collected_at=note.collected_at,
        original_url=f"https://www.xiaohongshu.com/explore/{note.note_id}",
    )


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


def load_fixture_items(seed_path: Path) -> list[IntelItem]:
    """读取演示数据，供前端纵向切片开发使用"""

    return load_seed_items(seed_path)


async def load_xiaohongshu_items(limit: int = 20) -> list[IntelItem]:
    """从现有 notes 集合读取实时小红书数据"""

    try:
        collection = mongodb.get_collection("notes")
    except RuntimeError:
        return []

    cursor = (
        collection.find({})
        .sort("collected_at", -1)
        .limit(limit)
    )
    raw_rows = await cursor.to_list(length=limit)

    return [note_to_intel_item(Note(**row)) for row in raw_rows]


async def build_overview_feed(seed_path: Path, live_limit: int = 20) -> list[IntelItem]:
    """构建总览页所需的统一情报流"""

    fixture_items = load_fixture_items(seed_path)
    live_xhs_items = await load_xiaohongshu_items(limit=live_limit)
    non_xhs_fixture_items = [
        item for item in fixture_items if item.source_type != IntelSourceType.XIAOHONGSHU
    ]

    if live_xhs_items:
        return live_xhs_items + non_xhs_fixture_items

    return fixture_items


def build_source_feed(items: Iterable[IntelItem], source_key: str) -> list[IntelItem]:
    """按来源筛出详情页数据"""

    return [item for item in items if item.source_type.value == source_key]
