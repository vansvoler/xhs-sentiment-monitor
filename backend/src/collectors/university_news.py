"""海外大学官网新闻解析与采集辅助。"""

import json
import re
from datetime import datetime, timezone
from time import struct_time
from urllib.parse import urljoin

import feedparser  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from src.collectors.university_sources import UNIVERSITY_SOURCES, IntelSource
from src.models.intel import (
    IntelItem,
    IntelSourceSyncReport,
    IntelSourceSyncStatus,
)
from src.utils.intel_utils import infer_impact_targets

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class SourceBlockedError(RuntimeError):
    """来源被反爬或挑战页拦截。"""


def build_item_id(source_id: str, canonical_key: str) -> str:
    """生成统一 item_id。"""

    return f"{source_id}:{canonical_key}"


def _coerce_datetime(raw_value: object, collected_at: datetime) -> datetime:
    if isinstance(raw_value, datetime):
        return raw_value.astimezone(timezone.utc)

    if isinstance(raw_value, struct_time):
        return datetime(
            raw_value.tm_year,
            raw_value.tm_mon,
            raw_value.tm_mday,
            raw_value.tm_hour,
            raw_value.tm_min,
            raw_value.tm_sec,
            tzinfo=timezone.utc,
        )

    if isinstance(raw_value, tuple) and len(raw_value) >= 6:
        return datetime(
            int(raw_value[0]),
            int(raw_value[1]),
            int(raw_value[2]),
            int(raw_value[3]),
            int(raw_value[4]),
            int(raw_value[5]),
            tzinfo=timezone.utc,
        )

    if isinstance(raw_value, str):
        normalized = raw_value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).astimezone(timezone.utc)
        except ValueError:
            return datetime.strptime(normalized, "%d %B %Y").replace(
                tzinfo=timezone.utc
            )

    return collected_at.astimezone(timezone.utc)


def _build_item(
    source: IntelSource,
    title: str,
    link: str,
    summary: str,
    published_at: datetime,
    collected_at: datetime,
    external_id: str | None = None,
    content_html: str | None = None,
) -> IntelItem:
    item = source.build_item(
        title=title,
        link=link,
        summary=summary,
        published_at=published_at.astimezone(timezone.utc),
        collected_at=collected_at.astimezone(timezone.utc),
        external_id=external_id,
        content_html=content_html,
        impact_targets=infer_impact_targets(title, summary),
    )
    return item.model_copy(update={"item_id": build_item_id(source.source_id, link)})


def normalize_feed_entry(
    source: IntelSource,
    entry: dict[str, object],
    collected_at: datetime,
) -> IntelItem:
    """把通用 RSS/Atom entry 归一化为 IntelItem。"""

    title = str(entry["title"])
    link = str(entry["link"])
    summary = str(entry.get("summary") or entry.get("description") or title)
    published_at = _coerce_datetime(
        entry.get("published_parsed")
        or entry.get("updated_parsed")
        or entry.get("published"),
        collected_at,
    )

    return _build_item(
        source=source,
        title=title,
        link=link,
        summary=summary,
        published_at=published_at,
        collected_at=collected_at,
        external_id=str(entry.get("id")) if entry.get("id") else None,
        content_html=str(entry.get("content")) if entry.get("content") else None,
    )


def normalize_ucl_result(
    source: IntelSource,
    result: dict[str, object],
    collected_at: datetime,
) -> IntelItem:
    """把 UCL Funnelback JSON 结果归一化。"""

    title = str(result["title"])
    link = str(result.get("liveUrl") or result.get("link"))
    summary = str(result.get("summary") or title)
    published_at = _coerce_datetime(
        result.get("date") or result.get("publishedDate"),
        collected_at,
    )

    return _build_item(
        source=source,
        title=title,
        link=link,
        summary=summary,
        published_at=published_at,
        collected_at=collected_at,
    )


def normalize_imperial_result(
    source: IntelSource,
    result: dict[str, object],
    collected_at: datetime,
) -> IntelItem:
    """把 Imperial JSON feed 结果归一化。"""

    title = str(result["headline"])
    article_url = str(result["articleURL"])
    link = urljoin("https://www.imperial.ac.uk", article_url)
    summary = str(result.get("summary") or title)
    published_at = _coerce_datetime(
        result.get("sortDate") or result.get("date"), collected_at
    )

    return _build_item(
        source=source,
        title=title,
        link=link,
        summary=summary,
        published_at=published_at,
        collected_at=collected_at,
        external_id=str(result.get("contentID")) if result.get("contentID") else None,
    )


def parse_oxford_listing(
    source: IntelSource,
    html: str,
    collected_at: datetime,
) -> list[IntelItem]:
    """解析 Oxford 新闻列表页。"""

    if (
        "Just a moment..." in html
        or "Enable JavaScript and cookies to continue" in html
        or "__cf_chl_" in html
    ):
        raise SourceBlockedError("Cloudflare challenge")

    soup = BeautifulSoup(html, "html.parser")
    items: list[IntelItem] = []

    for article in soup.select("article"):
        link_node = article.select_one("h3 a")
        if link_node is None or not link_node.get("href"):
            continue

        title = link_node.get_text(strip=True)
        href = str(link_node.get("href"))
        link = urljoin(str(source.listing_url), href)
        summary_node = article.select_one("p")
        summary = summary_node.get_text(strip=True) if summary_node else title
        time_node = article.select_one("time")
        published_at = _coerce_datetime(
            time_node.get("datetime") if time_node else None,
            collected_at,
        )

        items.append(
            _build_item(
                source=source,
                title=title,
                link=link,
                summary=summary,
                published_at=published_at,
                collected_at=collected_at,
            )
        )

    return items


def parse_configured_html_listing(
    source: IntelSource,
    html: str,
    collected_at: datetime,
) -> list[IntelItem]:
    """按配置化 CSS selector 解析通用 HTML 列表页。"""

    if source.selectors is None:
        raise ValueError(f"{source.source_id} missing listing selectors")

    soup = BeautifulSoup(html, "html.parser")
    selectors = source.selectors
    items: list[IntelItem] = []

    for node in soup.select(selectors.item):
        title_node = node.select_one(selectors.title)
        url_node = node.select_one(selectors.url)
        href = url_node.get("href") if url_node else None
        if title_node is None or not href:
            continue

        title = title_node.get_text(strip=True)
        link = urljoin(str(source.listing_url), str(href))
        summary_node = node.select_one(selectors.summary) if selectors.summary else None
        summary = summary_node.get_text(strip=True) if summary_node else title
        date_node = node.select_one(selectors.date) if selectors.date else None
        published_at = _coerce_datetime(
            date_node.get("datetime") if date_node else None,
            collected_at,
        )

        items.append(
            _build_item(
                source=source,
                title=title,
                link=link,
                summary=summary,
                published_at=published_at,
                collected_at=collected_at,
            )
        )

    return items


def _extract_ucl_results(payload: dict[str, object]) -> list[dict[str, object]]:
    results = payload.get("results")
    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]

    response = payload.get("response")
    if not isinstance(response, dict):
        return []

    result_packet = response.get("resultPacket")
    if not isinstance(result_packet, dict):
        return []

    raw_results = result_packet.get("results")
    if not isinstance(raw_results, list):
        return []

    return [item for item in raw_results if isinstance(item, dict)]


async def _load_json_payload(response) -> dict[str, object]:
    try:
        return await response.json()
    except json.JSONDecodeError:
        raw_text = await response.text()
        sanitized = re.sub(r",(\s*[\]}])", r"\1", raw_text)
        return json.loads(sanitized)


async def collect_feed_items(session, source: IntelSource) -> list[IntelItem]:
    """抓取并解析 feed / JSON feed 类型来源。"""

    if source.feed_url is None:
        return []

    collected_at = datetime.now(timezone.utc)
    feed_url = str(source.feed_url)

    async with session.get(feed_url, headers=DEFAULT_REQUEST_HEADERS) as response:
        response.raise_for_status()
        if "search.json" in feed_url:
            payload = await _load_json_payload(response)
            return [
                normalize_ucl_result(source, result, collected_at)
                for result in _extract_ucl_results(payload)
            ]
        if "articles.json" in feed_url:
            payload = await _load_json_payload(response)
            raw_articles = payload.get("articles")
            if not isinstance(raw_articles, list):
                return []
            return [
                normalize_imperial_result(source, result, collected_at)
                for result in raw_articles
                if isinstance(result, dict)
            ]

        payload_text = await response.text()

    parsed = feedparser.parse(payload_text)
    return [
        normalize_feed_entry(source, dict(entry), collected_at)
        for entry in parsed.entries
    ]


async def collect_listing_items(session, source: IntelSource) -> list[IntelItem]:
    """抓取并解析静态 HTML 列表页来源。"""

    if source.listing_url is None:
        return []

    collected_at = datetime.now(timezone.utc)
    async with session.get(
        str(source.listing_url),
        headers=DEFAULT_REQUEST_HEADERS,
    ) as response:
        response.raise_for_status()
        html = await response.text()

    if source.adapter_type == "html_listing":
        return parse_configured_html_listing(source, html, collected_at)

    return parse_oxford_listing(source, html, collected_at)


async def collect_source_items(session, source: IntelSource) -> list[IntelItem]:
    """按适配器类型分发采集逻辑。"""

    if source.adapter_type in {"feed", "rss", "json_feed"}:
        return await collect_feed_items(session, source)

    return await collect_listing_items(session, source)


async def collect_all_university_news(
    session,
    sources: list[IntelSource] | None = None,
) -> list[IntelItem]:
    """采集全部启用的大学新闻信源。"""

    items, _reports = await collect_all_university_news_with_reports(session, sources)
    return items


async def collect_all_university_news_with_reports(
    session,
    sources: list[IntelSource] | None = None,
) -> tuple[list[IntelItem], list[IntelSourceSyncReport]]:
    """采集全部启用的大学新闻信源，并返回逐来源报告。

    ``sources`` 缺省时回退到模块级 ``UNIVERSITY_SOURCES``。生产路径（scheduler 经
    ``intel_ingest.sync_university_news``）会显式传入运行时重新读取的列表，从而支持
    通过 ``POST /api/intel/sources`` 动态新增的信源在下一轮调度立即生效。模块级常量
    仍然保留，以便测试通过 ``monkeypatch.setattr`` 注入 fixture。
    """

    effective_sources = sources if sources is not None else UNIVERSITY_SOURCES

    items: list[IntelItem] = []
    reports: list[IntelSourceSyncReport] = []
    synced_at = datetime.now(timezone.utc)

    for source in effective_sources:
        if not source.enabled:
            continue

        try:
            source_items = await collect_source_items(session, source)
        except SourceBlockedError as exc:
            reports.append(
                IntelSourceSyncReport(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    source_name=source.source_name,
                    school_name=source.school_name,
                    status=IntelSourceSyncStatus.BLOCKED,
                    error_message=str(exc),
                    synced_at=synced_at,
                )
            )
            continue
        except Exception as exc:
            reports.append(
                IntelSourceSyncReport(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    source_name=source.source_name,
                    school_name=source.school_name,
                    status=IntelSourceSyncStatus.ERROR,
                    error_message=str(exc),
                    synced_at=synced_at,
                )
            )
            continue

        items.extend(source_items)
        reports.append(
            IntelSourceSyncReport(
                source_id=source.source_id,
                source_type=source.source_type,
                source_name=source.source_name,
                school_name=source.school_name,
                status=IntelSourceSyncStatus.SUCCESS,
                item_count=len(source_items),
                synced_at=synced_at,
            )
        )

    return items, reports
