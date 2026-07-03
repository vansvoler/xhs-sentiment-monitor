"""UCAS 官网新闻采集与解析。"""

from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.models.intel import (
    IntelItem,
    IntelSourceSyncReport,
    IntelSourceSyncStatus,
    IntelSourceType,
)
from src.utils.intel_utils import infer_impact_targets

UCAS_NEWS_URL = "https://www.ucas.com/about-us/news-and-insights"
UCAS_SOURCE_ID = "ucas-news"
UCAS_SOURCE_NAME = "UCAS"

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def build_item_id(canonical_key: str) -> str:
    """生成统一 UCAS item_id。"""

    return f"{UCAS_SOURCE_ID}:{canonical_key}"


def _build_item(
    title: str,
    link: str,
    summary: str,
    published_at: datetime,
    collected_at: datetime,
) -> IntelItem:
    summary_short = summary[:80] if summary else title
    summary_long = summary[:180] if summary else title

    return IntelItem(
        item_id=build_item_id(link),
        source_type=IntelSourceType.UCAS,
        source_name=UCAS_SOURCE_NAME,
        title=title,
        summary_short=summary_short,
        summary_long=summary_long,
        impact_targets=infer_impact_targets(title, summary),
        published_at=published_at.astimezone(timezone.utc),
        collected_at=collected_at.astimezone(timezone.utc),
        original_url=link,
    )


def parse_ucas_latest_news(
    html: str,
    collected_at: datetime,
) -> list[IntelItem]:
    """解析 UCAS `Latest news` 列表。"""

    soup = BeautifulSoup(html, "html.parser")
    heading = next(
        (
            node
            for node in soup.find_all("h2")
            if node.get_text(strip=True) == "Latest news"
        ),
        None,
    )
    if heading is None:
        raise ValueError("UCAS latest news section not found")

    article = heading.find_parent("article")
    if article is None:
        raise ValueError("UCAS latest news article container not found")

    cards = article.select("div.content-section--snug.content-section--divider")
    if not cards:
        raise ValueError("UCAS latest news items not found")

    items: list[IntelItem] = []

    for card in cards:
        link_node = card.select_one("dt.card-font-rod a")
        time_node = card.select_one("dd time")
        summary_nodes = card.select("dd")
        if link_node is None or time_node is None or not link_node.get("href"):
            continue

        href = str(link_node.get("href"))
        raw_datetime = str(time_node.get("datetime"))
        title = link_node.get_text(strip=True)
        link = urljoin(UCAS_NEWS_URL, href)
        published_at = datetime.fromisoformat(raw_datetime).astimezone(timezone.utc)
        summary = title
        if len(summary_nodes) >= 3:
            candidate = summary_nodes[2].get_text(" ", strip=True)
            if candidate:
                summary = candidate

        items.append(
            _build_item(
                title=title,
                link=link,
                summary=summary,
                published_at=published_at,
                collected_at=collected_at,
            )
        )

    return items


async def collect_ucas_news(session) -> list[IntelItem]:
    """抓取 UCAS `Latest news`。"""

    collected_at = datetime.now(timezone.utc)
    async with session.get(UCAS_NEWS_URL, headers=DEFAULT_REQUEST_HEADERS) as response:
        response.raise_for_status()
        html = await response.text()

    return parse_ucas_latest_news(html, collected_at)


async def collect_ucas_news_with_report(
    session,
) -> tuple[list[IntelItem], IntelSourceSyncReport]:
    """抓取 UCAS 新闻并返回同步结果。"""

    synced_at = datetime.now(timezone.utc)

    try:
        items = await collect_ucas_news(session)
    except Exception as exc:
        return [], IntelSourceSyncReport(
            source_id=UCAS_SOURCE_ID,
            source_type=IntelSourceType.UCAS,
            source_name=UCAS_SOURCE_NAME,
            status=IntelSourceSyncStatus.ERROR,
            error_message=str(exc),
            synced_at=synced_at,
        )

    return items, IntelSourceSyncReport(
        source_id=UCAS_SOURCE_ID,
        source_type=IntelSourceType.UCAS,
        source_name=UCAS_SOURCE_NAME,
        status=IntelSourceSyncStatus.SUCCESS,
        item_count=len(items),
        synced_at=synced_at,
    )
