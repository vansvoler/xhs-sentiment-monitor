import json
from datetime import datetime, timezone

import pytest

from src.collectors.university_news import (
    DEFAULT_REQUEST_HEADERS,
    SourceBlockedError,
    build_item_id,
    collect_all_university_news,
    collect_all_university_news_with_reports,
    collect_feed_items,
    collect_listing_items,
    normalize_feed_entry,
    normalize_imperial_result,
    normalize_ucl_result,
    parse_configured_html_listing,
    parse_oxford_listing,
)
from src.collectors.university_sources import (
    UNIVERSITY_SOURCES,
    IntelSource,
    ListingSelectors,
)
from src.models.intel import IntelSourceType


def test_normalize_feed_entry_maps_cambridge_news():
    source = UNIVERSITY_SOURCES[1]
    entry = {
        "id": "https://www.cam.ac.uk/news/example-story",
        "title": "Example Cambridge story",
        "link": "https://www.cam.ac.uk/news/example-story",
        "summary": "Summary text",
        "published_parsed": (2026, 5, 21, 8, 0, 0, 0, 0, 0),
    }

    item = normalize_feed_entry(source, entry, collected_at=datetime.now(timezone.utc))

    assert item.school_name == "Cambridge"
    assert item.source_group == "重点学校"
    assert item.original_url == entry["link"]
    assert item.item_id == build_item_id(source.source_id, entry["link"])


def test_normalize_ucl_result_maps_json_feed():
    source = UNIVERSITY_SOURCES[2]
    result = {
        "title": "UCL launches new scholarship",
        "liveUrl": "https://www.ucl.ac.uk/news/2026/may/ucl-launches-new-scholarship",
        "date": "2026-05-21T09:30:00Z",
        "summary": "Scholarship summary",
    }

    item = normalize_ucl_result(source, result, collected_at=datetime.now(timezone.utc))

    assert item.school_name == "UCL"
    assert item.source_name == "UCL News"
    assert item.original_url == result["liveUrl"]
    assert item.summary_short == "Scholarship summary"


def test_normalize_imperial_result_maps_json_feed():
    source = UNIVERSITY_SOURCES[3]
    result = {
        "headline": "Imperial AI story",
        "articleURL": "/news/articles/2026/imperial-ai-story/",
        "date": "20 May 2026",
        "summary": "Imperial summary",
        "contentID": "1777344",
    }

    item = normalize_imperial_result(
        source,
        result,
        collected_at=datetime.now(timezone.utc),
    )

    assert item.school_name == "Imperial"
    assert item.original_url.endswith("/news/articles/2026/imperial-ai-story/")
    assert item.external_id == "1777344"


def test_parse_oxford_listing_extracts_cards():
    source = UNIVERSITY_SOURCES[0]
    html = """
    <div class="news-listing">
      <div class="view-content">
        <article>
          <h3><a href="/news/2026/example-story">Oxford story</a></h3>
          <time datetime="2026-05-20T09:00:00+00:00"></time>
          <p>Listing summary</p>
        </article>
      </div>
    </div>
    """

    items = parse_oxford_listing(source, html, collected_at=datetime.now(timezone.utc))

    assert len(items) == 1
    assert items[0].title == "Oxford story"
    assert items[0].school_name == "Oxford"


def test_parse_oxford_listing_raises_when_cloudflare_blocks():
    source = UNIVERSITY_SOURCES[0]
    html = """
    <!DOCTYPE html>
    <html lang="en-US">
      <head><title>Just a moment...</title></head>
      <body><span>Enable JavaScript and cookies to continue</span></body>
    </html>
    """

    with pytest.raises(SourceBlockedError):
        parse_oxford_listing(source, html, collected_at=datetime.now(timezone.utc))


def test_parse_configured_html_listing_extracts_cards():
    source = IntelSource(
        source_id="ukvi-news",
        source_type=IntelSourceType.VISA_POLICY,
        source_name="UKVI News",
        source_group="签证政策",
        adapter_type="html_listing",
        listing_url="https://www.gov.uk/search/news-and-communications",
        selectors=ListingSelectors(
            item="article",
            title="h2 a",
            url="h2 a",
            summary="p",
            date="time",
        ),
    )
    html = """
    <article>
      <h2><a href="/government/news/student-visa-update">Student visa update</a></h2>
      <time datetime="2026-05-20T09:00:00+00:00"></time>
      <p>Visa policy summary</p>
    </article>
    """

    items = parse_configured_html_listing(
        source,
        html,
        collected_at=datetime.now(timezone.utc),
    )

    assert len(items) == 1
    assert items[0].source_type == IntelSourceType.VISA_POLICY
    assert items[0].source_name == "UKVI News"
    assert items[0].title == "Student visa update"
    assert items[0].summary_short == "Visa policy summary"
    assert items[0].original_url == (
        "https://www.gov.uk/government/news/student-visa-update"
    )


class _FakeResponse:
    def __init__(
        self,
        text_data: str = "",
        json_data: dict | None = None,
        json_error: Exception | None = None,
        http_error: Exception | None = None,
    ) -> None:
        self._text_data = text_data
        self._json_data = json_data or {}
        self._json_error = json_error
        self._http_error = http_error

    def raise_for_status(self) -> None:
        if self._http_error is not None:
            raise self._http_error

    async def text(self) -> str:
        return self._text_data

    async def json(self) -> dict:
        if self._json_error is not None:
            raise self._json_error
        return self._json_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.requested_urls: list[str] = []
        self.requested_headers: list[dict[str, str]] = []

    def get(self, url: str, **kwargs):
        self.requested_urls.append(url)
        self.requested_headers.append(kwargs.get("headers", {}))
        return self.response


@pytest.mark.asyncio
async def test_collect_feed_items_parses_rss_payload():
    source = UNIVERSITY_SOURCES[1]
    session = _FakeSession(_FakeResponse(text_data="""
            <rss version="2.0">
              <channel>
                <item>
                  <title>Cambridge RSS story</title>
                  <link>https://www.cam.ac.uk/news/rss-story</link>
                  <description>RSS summary</description>
                  <pubDate>Wed, 21 May 2026 08:00:00 GMT</pubDate>
                  <guid>cambridge-rss-story</guid>
                </item>
              </channel>
            </rss>
            """))

    items = await collect_feed_items(session, source)

    assert len(items) == 1
    assert items[0].title == "Cambridge RSS story"
    assert session.requested_urls == [str(source.feed_url)]
    assert (
        session.requested_headers[0]["User-Agent"]
        == DEFAULT_REQUEST_HEADERS["User-Agent"]
    )


@pytest.mark.asyncio
async def test_collect_feed_items_raises_http_error():
    source = UNIVERSITY_SOURCES[1]
    session = _FakeSession(_FakeResponse(http_error=RuntimeError("403 forbidden")))

    with pytest.raises(RuntimeError, match="403 forbidden"):
        await collect_feed_items(session, source)


@pytest.mark.asyncio
async def test_collect_feed_items_parses_ucl_json_payload():
    source = UNIVERSITY_SOURCES[2]
    session = _FakeSession(
        _FakeResponse(
            json_data={
                "results": [
                    {
                        "title": "UCL JSON story",
                        "liveUrl": "https://www.ucl.ac.uk/news/ucl-json-story",
                        "date": "2026-05-21T08:00:00Z",
                        "summary": "JSON summary",
                    }
                ]
            }
        )
    )

    items = await collect_feed_items(session, source)

    assert len(items) == 1
    assert items[0].title == "UCL JSON story"


@pytest.mark.asyncio
async def test_collect_feed_items_parses_imperial_json_payload():
    source = UNIVERSITY_SOURCES[3]
    session = _FakeSession(
        _FakeResponse(
            json_data={
                "articles": [
                    {
                        "headline": "Imperial JSON story",
                        "articleURL": "/news/articles/2026/imperial-json-story/",
                        "date": "20 May 2026",
                        "summary": "Imperial JSON summary",
                        "contentID": "1777345",
                    }
                ]
            }
        )
    )

    items = await collect_feed_items(session, source)

    assert len(items) == 1
    assert items[0].title == "Imperial JSON story"
    assert items[0].school_name == "Imperial"


@pytest.mark.asyncio
async def test_collect_feed_items_sanitizes_invalid_imperial_json():
    source = UNIVERSITY_SOURCES[3]
    session = _FakeSession(
        _FakeResponse(
            text_data=(
                '{"articles":[{"headline":"Imperial trailing comma story",'
                '"articleURL":"/news/articles/2026/imperial-trailing-comma-story/",'
                '"date":"20 May 2026",'
                '"summary":"Imperial summary",'
                '"contentID":"1777346"},]}'
            ),
            json_error=json.JSONDecodeError("Expecting value", "", 0),
        )
    )

    items = await collect_feed_items(session, source)

    assert len(items) == 1
    assert items[0].title == "Imperial trailing comma story"


@pytest.mark.asyncio
async def test_collect_listing_items_parses_oxford_html():
    source = UNIVERSITY_SOURCES[0]
    session = _FakeSession(_FakeResponse(text_data="""
            <article>
              <h3><a href="/news/2026/listing-story">Oxford listing story</a></h3>
              <time datetime="2026-05-20T09:00:00+00:00"></time>
              <p>Oxford listing summary</p>
            </article>
            """))

    items = await collect_listing_items(session, source)

    assert len(items) == 1
    assert items[0].title == "Oxford listing story"


@pytest.mark.asyncio
async def test_collect_all_university_news_skips_disabled_sources(monkeypatch):
    calls = []

    async def fake_collect_source(_session, source):
        calls.append(source.source_id)
        return []

    monkeypatch.setattr(
        "src.collectors.university_news.collect_source_items",
        fake_collect_source,
    )

    await collect_all_university_news(session=None)

    assert "oxford-news" in calls
    assert {"cambridge-news", "ucl-news", "imperial-news"}.issubset(calls)


@pytest.mark.asyncio
async def test_collect_all_university_news_with_reports_marks_blocked_source(
    monkeypatch,
):
    async def fake_collect_source(_session, source):
        if source.source_id == "oxford-news":
            raise SourceBlockedError("Cloudflare challenge")
        return []

    monkeypatch.setattr(
        "src.collectors.university_news.collect_source_items",
        fake_collect_source,
    )

    items, reports = await collect_all_university_news_with_reports(session=None)

    assert items == []
    oxford_report = next(
        report for report in reports if report.source_id == "oxford-news"
    )
    assert oxford_report.status == "blocked"
    assert oxford_report.error_message == "Cloudflare challenge"


@pytest.mark.asyncio
async def test_collect_all_university_news_with_reports_preserves_source_type(
    monkeypatch,
):
    source = IntelSource(
        source_id="ukvi-news",
        source_type=IntelSourceType.VISA_POLICY,
        source_name="UKVI News",
        source_group="签证政策",
        adapter_type="feed",
        feed_url="https://www.gov.uk/news.atom",
    )

    async def fake_collect_source(_session, configured_source):
        return [
            configured_source.build_item(
                title="Student visa update",
                link="https://www.gov.uk/student-visa-update",
                summary="Visa policy summary",
                published_at=datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
                collected_at=datetime(2026, 5, 20, 9, 5, tzinfo=timezone.utc),
            )
        ]

    monkeypatch.setattr("src.collectors.university_news.UNIVERSITY_SOURCES", [source])
    monkeypatch.setattr(
        "src.collectors.university_news.collect_source_items",
        fake_collect_source,
    )

    items, reports = await collect_all_university_news_with_reports(session=None)

    assert items[0].source_type == IntelSourceType.VISA_POLICY
    assert reports[0].source_type == IntelSourceType.VISA_POLICY
