import pytest

from src.collectors.intel_source_probe import (
    infer_html_listing_selectors,
    probe_intel_source,
)


class _FakeResponse:
    def __init__(self, text_data: str, content_type: str = "text/html") -> None:
        self._text_data = text_data
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self) -> None:
        return None

    async def text(self) -> str:
        return self._text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, responses: dict[str, _FakeResponse]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def get(self, url: str, **_kwargs):
        self.requested_urls.append(url)
        return self.responses[url]


@pytest.mark.asyncio
async def test_probe_intel_source_prefers_discovered_rss_link():
    page_url = "https://example.com/news"
    feed_url = "https://example.com/news/feed.xml"
    session = _FakeSession(
        {
            page_url: _FakeResponse(f"""
                <html>
                  <head>
                    <link
                      rel="alternate"
                      type="application/rss+xml"
                      href="{feed_url}"
                    />
                  </head>
                  <body></body>
                </html>
                """),
            feed_url: _FakeResponse(
                """
                <rss version="2.0">
                  <channel>
                    <item>
                      <title>Example RSS story</title>
                      <link>https://example.com/news/rss-story</link>
                    </item>
                  </channel>
                </rss>
                """,
                content_type="application/rss+xml",
            ),
        }
    )

    result = await probe_intel_source(
        session,
        page_url,
        source_id="example-news",
        source_name="Example News",
        source_group="测试来源",
        source_type="visa_policy",
    )

    assert result.status == "success"
    assert result.recommended_source.adapter_type == "feed"
    assert result.recommended_source.feed_url == feed_url
    assert result.sample_count == 1


def test_infer_html_listing_selectors_from_article_cards():
    html = """
    <main>
      <article>
        <h2><a href="/news/story-a">Story A</a></h2>
        <time datetime="2026-05-27T09:00:00+00:00"></time>
        <p>Summary A</p>
      </article>
      <article>
        <h2><a href="/news/story-b">Story B</a></h2>
        <time datetime="2026-05-26T09:00:00+00:00"></time>
        <p>Summary B</p>
      </article>
    </main>
    """

    selectors = infer_html_listing_selectors(html)

    assert selectors is not None
    assert selectors.item == "article"
    assert selectors.title == "h2 a"
    assert selectors.url == "h2 a"
    assert selectors.summary == "p"
    assert selectors.date == "time"
