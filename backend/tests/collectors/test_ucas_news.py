from datetime import datetime, timezone

import pytest

from src.collectors.ucas_news import (
    DEFAULT_REQUEST_HEADERS,
    UCAS_NEWS_URL,
    build_item_id,
    collect_ucas_news,
    collect_ucas_news_with_report,
    parse_ucas_latest_news,
)
from src.models.intel import IntelSourceSyncStatus, IntelSourceType


def test_parse_ucas_latest_news_extracts_cards():
    html = """
    <article class="card elevation-low">
      <header class="card__section">
        <div class="heading-with-meta">
          <h2>Latest news</h2>
        </div>
      </header>
      <div class="card__section">
        <dl class="list list--vertical-group">
          <div class="content-section--snug content-section--divider">
            <dd></dd>
            <dt class="card-font-rod">
              <a href="/corporate/news-and-key-documents/news/example-story">
                Example UCAS story
              </a>
            </dt>
            <dd><time datetime="2026-05-21T08:00:00+00:00">21 May 2026</time></dd>
            <dd>UCAS summary text</dd>
          </div>
        </dl>
      </div>
    </article>
    """

    items = parse_ucas_latest_news(html, collected_at=datetime.now(timezone.utc))

    assert len(items) == 1
    assert items[0].source_type == IntelSourceType.UCAS
    assert items[0].title == "Example UCAS story"
    assert items[0].summary_short == "UCAS summary text"
    assert items[0].original_url.endswith(
        "/corporate/news-and-key-documents/news/example-story"
    )
    assert items[0].item_id == build_item_id(items[0].original_url)


class _FakeResponse:
    def __init__(
        self,
        text_data: str,
        http_error: Exception | None = None,
    ) -> None:
        self._text_data = text_data
        self._http_error = http_error

    def raise_for_status(self) -> None:
        if self._http_error is not None:
            raise self._http_error

    async def text(self) -> str:
        return self._text_data

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
async def test_collect_ucas_news_requests_live_page():
    session = _FakeSession(_FakeResponse("""
            <article>
              <h2>Latest news</h2>
              <div class="content-section--snug content-section--divider">
                <dt class="card-font-rod">
                  <a href="/corporate/news-and-key-documents/news/example-story">
                    Example UCAS story
                  </a>
                </dt>
                <dd><time datetime="2026-05-21T08:00:00+00:00">21 May 2026</time></dd>
                <dd>UCAS summary text</dd>
              </div>
            </article>
            """))

    items = await collect_ucas_news(session)

    assert len(items) == 1
    assert session.requested_urls == [UCAS_NEWS_URL]
    assert (
        session.requested_headers[0]["User-Agent"]
        == DEFAULT_REQUEST_HEADERS["User-Agent"]
    )


@pytest.mark.asyncio
async def test_collect_ucas_news_with_report_marks_success():
    session = _FakeSession(_FakeResponse("""
            <article>
              <h2>Latest news</h2>
              <div class="content-section--snug content-section--divider">
                <dt class="card-font-rod">
                  <a href="/corporate/news-and-key-documents/news/example-story">
                    Example UCAS story
                  </a>
                </dt>
                <dd><time datetime="2026-05-21T08:00:00+00:00">21 May 2026</time></dd>
                <dd>UCAS summary text</dd>
              </div>
            </article>
            """))

    items, report = await collect_ucas_news_with_report(session)

    assert len(items) == 1
    assert report.status == IntelSourceSyncStatus.SUCCESS
    assert report.item_count == 1


@pytest.mark.asyncio
async def test_collect_ucas_news_with_report_marks_error():
    session = _FakeSession(_FakeResponse("<html></html>"))

    items, report = await collect_ucas_news_with_report(session)

    assert items == []
    assert report.status == IntelSourceSyncStatus.ERROR
    assert report.item_count == 0


@pytest.mark.asyncio
async def test_collect_ucas_news_with_report_marks_http_error():
    session = _FakeSession(
        _FakeResponse("", http_error=RuntimeError("503 unavailable"))
    )

    items, report = await collect_ucas_news_with_report(session)

    assert items == []
    assert report.status == IntelSourceSyncStatus.ERROR
    assert report.error_message == "503 unavailable"
