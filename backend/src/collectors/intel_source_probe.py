"""官网情报信源自动探测。"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import aiohttp
import feedparser  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from src.collectors.university_news import DEFAULT_REQUEST_HEADERS
from src.collectors.university_sources import IntelSource, ListingSelectors
from src.models.intel import IntelSourceType

FEED_LINK_TYPES = {
    "application/rss+xml",
    "application/atom+xml",
    "application/feed+json",
    "application/json",
}

HTML_ITEM_SELECTORS = [
    "article",
    ".news-item",
    ".views-row",
    ".search-result",
    ".card",
    "li",
]

TITLE_SELECTORS = ["h2 a", "h3 a", "h4 a", "a"]
SUMMARY_SELECTORS = ["p", ".summary", ".description", ".excerpt"]
DATE_SELECTORS = ["time", ".date", ".published", ".publication-date"]


@dataclass(frozen=True)
class ProbeResult:
    """单个 URL 探测结果。"""

    status: str
    recommended_source: IntelSource
    sample_count: int
    message: str


def _looks_blocked(text: str) -> bool:
    return (
        "Just a moment..." in text
        or "Enable JavaScript and cookies to continue" in text
        or "__cf_chl_" in text
    )


def _count_feed_entries(text: str) -> int:
    parsed = feedparser.parse(text)
    return len(parsed.entries)


def _discover_feed_urls(page_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []

    for node in soup.select("link[rel~='alternate']"):
        href = node.get("href")
        node_type = str(node.get("type") or "").lower()
        if href and node_type in FEED_LINK_TYPES:
            urls.append(urljoin(page_url, str(href)))

    parsed = urlparse(page_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    candidates = [
        urljoin(page_url.rstrip("/") + "/", "feed"),
        urljoin(page_url.rstrip("/") + "/", "rss"),
        urljoin(page_url.rstrip("/") + "/", "feed.xml"),
        urljoin(root, "/feed"),
        urljoin(root, "/rss"),
    ]

    return list(dict.fromkeys([*urls, *candidates]))


def infer_html_listing_selectors(html: str) -> ListingSelectors | None:
    """从静态 HTML 中推断列表页 CSS selector。"""

    soup = BeautifulSoup(html, "html.parser")

    for item_selector in HTML_ITEM_SELECTORS:
        nodes = soup.select(item_selector)
        usable_nodes = [node for node in nodes if node.select_one("a[href]")]
        if len(usable_nodes) < 2:
            continue

        for title_selector in TITLE_SELECTORS:
            linked_titles = []
            for node in usable_nodes:
                title_node = node.select_one(title_selector)
                if title_node is not None and title_node.get("href"):
                    linked_titles.append(node)

            if len(linked_titles) < 2:
                continue

            summary = next(
                (
                    selector
                    for selector in SUMMARY_SELECTORS
                    if linked_titles[0].select_one(selector)
                ),
                None,
            )
            date = next(
                (
                    selector
                    for selector in DATE_SELECTORS
                    if linked_titles[0].select_one(selector)
                ),
                None,
            )

            return ListingSelectors(
                item=item_selector,
                title=title_selector,
                url=title_selector,
                summary=summary,
                date=date,
            )

    return None


async def _fetch_text(session, url: str) -> tuple[str, str]:
    async with session.get(url, headers=DEFAULT_REQUEST_HEADERS) as response:
        response.raise_for_status()
        return await response.text(), str(response.headers.get("Content-Type", ""))


async def _first_working_feed(
    session,
    page_url: str,
    html: str,
) -> tuple[str, int] | None:
    for feed_url in _discover_feed_urls(page_url, html):
        try:
            text, _content_type = await _fetch_text(session, feed_url)
        except Exception:
            continue

        sample_count = _count_feed_entries(text)
        if sample_count > 0:
            return feed_url, sample_count

    return None


def _default_source_id(url: str) -> str:
    netloc = urlparse(url).netloc.replace("www.", "")
    stem = re.sub(r"[^a-z0-9]+", "-", netloc.lower()).strip("-")
    return f"{stem}-news" if stem else "configured-news"


async def probe_intel_source(
    session,
    url: str,
    *,
    source_id: str | None = None,
    source_name: str | None = None,
    source_group: str = "自定义来源",
    source_type: str = "university_site",
) -> ProbeResult:
    """探测 URL 并返回推荐信源配置。"""

    text, content_type = await _fetch_text(session, url)
    source_id = source_id or _default_source_id(url)
    source_name = source_name or urlparse(url).netloc.replace("www.", "")
    source_type_value = IntelSourceType(source_type)

    if _looks_blocked(text):
        return ProbeResult(
            status="blocked",
            sample_count=0,
            message="页面疑似被反爬挑战拦截，需要 browser fallback。",
            recommended_source=IntelSource(
                source_id=source_id,
                source_type=source_type_value,
                source_name=source_name,
                source_group=source_group,
                adapter_type="html_listing",
                listing_url=url,
            ),
        )

    direct_feed_count = _count_feed_entries(text)
    if direct_feed_count > 0:
        return ProbeResult(
            status="success",
            sample_count=direct_feed_count,
            message="URL 本身就是可解析 feed。",
            recommended_source=IntelSource(
                source_id=source_id,
                source_type=source_type_value,
                source_name=source_name,
                source_group=source_group,
                adapter_type="feed",
                feed_url=url,
            ),
        )

    if "html" in content_type.lower() or "<html" in text.lower():
        feed_result = await _first_working_feed(session, url, text)
        if feed_result is not None:
            feed_url, sample_count = feed_result
            return ProbeResult(
                status="success",
                sample_count=sample_count,
                message="页面中发现可用 feed。",
                recommended_source=IntelSource(
                    source_id=source_id,
                    source_type=source_type_value,
                    source_name=source_name,
                    source_group=source_group,
                    adapter_type="feed",
                    feed_url=feed_url,
                ),
            )

        selectors = infer_html_listing_selectors(text)
        if selectors is not None:
            return ProbeResult(
                status="success",
                sample_count=0,
                message="未发现 feed，已推断静态 HTML 列表页 selectors。",
                recommended_source=IntelSource(
                    source_id=source_id,
                    source_type=source_type_value,
                    source_name=source_name,
                    source_group=source_group,
                    adapter_type="html_listing",
                    listing_url=url,
                    selectors=selectors,
                ),
            )

    return ProbeResult(
        status="unsupported",
        sample_count=0,
        message="未识别出 feed 或稳定静态列表结构。",
        recommended_source=IntelSource(
            source_id=source_id,
            source_type=source_type_value,
            source_name=source_name,
            source_group=source_group,
            adapter_type="html_listing",
            listing_url=url,
        ),
    )


def _dump_recommendation(result: ProbeResult) -> str:
    payload = {
        "status": result.status,
        "message": result.message,
        "sample_count": result.sample_count,
        "recommended_config": result.recommended_source.model_dump(
            mode="json",
            exclude_none=True,
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


async def _main_async(args: argparse.Namespace) -> int:
    async with aiohttp.ClientSession() as session:
        result = await probe_intel_source(
            session,
            args.url,
            source_id=args.source_id,
            source_name=args.source_name,
            source_group=args.source_group,
            source_type=args.source_type,
        )

    print(_dump_recommendation(result))
    return 0 if result.status == "success" else 2


def main() -> None:
    parser = argparse.ArgumentParser(description="探测官网情报信源抓取方案")
    parser.add_argument("url")
    parser.add_argument("--source-id")
    parser.add_argument("--source-name")
    parser.add_argument("--source-group", default="自定义来源")
    parser.add_argument("--source-type", default="university_site")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
