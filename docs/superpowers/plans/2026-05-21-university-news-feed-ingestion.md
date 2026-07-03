# University News Feed Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first real university news ingestion slice for Oxford, Cambridge, UCL, and Imperial, normalize the items into `intel_items`, and serve them through the existing intel API with fixture fallback.

**Architecture:** The backend keeps a Python-only ingestion path. Source discovery is configuration-driven: each school is defined in a source registry with an adapter type of `feed` or `listing`. Adapters fetch upstream data, normalize it into `IntelItem`, and upsert it into MongoDB; the existing intel API then prefers live `intel_items` before falling back to fixture data.

**Tech Stack:** FastAPI, Pydantic v2, aiohttp, MongoDB via Motor, pytest, pytest-asyncio, uv

---

## File Structure

- Create: `backend/src/collectors/university_sources.py`
  - Declares the source registry for Oxford, Cambridge, UCL, and Imperial.
- Create: `backend/src/collectors/university_news.py`
  - Implements `feed` and `listing` collectors plus normalization helpers.
- Create: `backend/tests/collectors/test_university_sources.py`
  - Verifies source registry shape and adapter assignments.
- Create: `backend/tests/collectors/test_university_news.py`
  - Verifies parsing and normalization for feed and listing payloads.
- Modify: `backend/src/models/intel.py`
  - Adds metadata needed for real university items and source sync state.
- Create: `backend/src/services/intel_ingest.py`
  - Coordinates source collection and MongoDB upsert.
- Create: `backend/tests/services/test_intel_ingest.py`
  - Verifies dedupe, upsert payload, and error isolation.
- Modify: `backend/src/services/intel_feed.py`
  - Loads real `intel_items` for university and UCAS sources before fixture fallback.
- Modify: `backend/src/api/intel.py`
  - Uses live-source reads consistently for source details and overview.
- Modify: `backend/tests/services/test_intel_feed.py`
  - Covers live-university reads and fallback behavior.
- Modify: `backend/tests/api/test_intel_api.py`
  - Covers live API output for `/overview` and `/sources/university_site`.
- Modify: `backend/pyproject.toml`
  - Adds `feedparser` and `beautifulsoup4` for source parsing.

### Task 1: Add dependencies and source registry

**Files:**
- Create: `backend/src/collectors/university_sources.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/collectors/test_university_sources.py`

- [ ] **Step 1: Write the failing source-registry test**

```python
from src.collectors.university_sources import UNIVERSITY_SOURCES


def test_university_sources_cover_first_wave_sites():
    assert [source.source_id for source in UNIVERSITY_SOURCES] == [
        "oxford-news",
        "cambridge-news",
        "ucl-news",
        "imperial-news",
    ]
    assert UNIVERSITY_SOURCES[0].adapter_type == "listing"
    assert UNIVERSITY_SOURCES[1].adapter_type == "feed"
    assert UNIVERSITY_SOURCES[2].adapter_type == "feed"
    assert UNIVERSITY_SOURCES[3].adapter_type == "feed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/collectors/test_university_sources.py -v`

Expected: FAIL with `ModuleNotFoundError` or missing `UNIVERSITY_SOURCES`.

- [ ] **Step 3: Add parser dependencies**

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "websockets>=13.0",
    "motor>=3.6.0",
    "redis>=5.2.0",
    "apscheduler>=3.10.0",
    "aiohttp>=3.11.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "openai>=1.0.0",
    "feedparser>=6.0.11",
    "beautifulsoup4>=4.12.3",
]
```

- [ ] **Step 4: Add the minimal source registry implementation**

```python
from pydantic import BaseModel, HttpUrl


class UniversitySource(BaseModel):
    source_id: str
    school_name: str
    adapter_type: str
    source_group: str
    source_name: str
    feed_url: HttpUrl | None = None
    listing_url: HttpUrl | None = None
    enabled: bool = True


UNIVERSITY_SOURCES = [
    UniversitySource(
        source_id="oxford-news",
        school_name="Oxford",
        adapter_type="listing",
        source_group="重点学校",
        source_name="Oxford News",
        listing_url="https://www.ox.ac.uk/News-listing?category=All",
    ),
    UniversitySource(
        source_id="cambridge-news",
        school_name="Cambridge",
        adapter_type="feed",
        source_group="重点学校",
        source_name="Cambridge News",
        feed_url="https://www.cam.ac.uk/news/feed",
    ),
]
```

- [ ] **Step 5: Expand registry to all four schools and re-run the test**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/collectors/test_university_sources.py -v`

Expected: PASS with `1 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml \
  backend/src/collectors/university_sources.py \
  backend/tests/collectors/test_university_sources.py
git commit -m "feat: add university news source registry"
```

### Task 2: Build feed and listing adapters with normalization

**Files:**
- Create: `backend/src/collectors/university_news.py`
- Modify: `backend/src/models/intel.py`
- Test: `backend/tests/collectors/test_university_news.py`

- [ ] **Step 1: Write the failing normalization tests**

```python
from datetime import datetime, timezone

from src.collectors.university_news import (
    build_item_id,
    normalize_feed_entry,
    parse_oxford_listing,
)
from src.collectors.university_sources import UNIVERSITY_SOURCES


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


def test_parse_oxford_listing_extracts_cards():
    source = UNIVERSITY_SOURCES[0]
    html = '''
    <div class="news-listing">
      <div class="view-content">
        <article>
          <h3><a href="/news/2026/example-story">Oxford story</a></h3>
          <time datetime="2026-05-20T09:00:00+00:00"></time>
          <p>Listing summary</p>
        </article>
      </div>
    </div>
    '''

    items = parse_oxford_listing(source, html, collected_at=datetime.now(timezone.utc))

    assert len(items) == 1
    assert items[0].title == "Oxford story"
    assert items[0].school_name == "Oxford"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/collectors/test_university_news.py -v`

Expected: FAIL because the module and helpers do not exist.

- [ ] **Step 3: Add minimal model fields for live-source metadata**

```python
class IntelItem(BaseModel):
    item_id: str
    source_type: IntelSourceType
    source_name: str
    title: str
    summary_short: str
    summary_long: str
    impact_targets: list[str] = Field(default_factory=list)
    published_at: datetime
    collected_at: datetime
    original_url: str
    priority_hint: str | None = None
    school_name: str | None = None
    source_group: str | None = None
    external_id: str | None = None
    content_html: str | None = None
```

- [ ] **Step 4: Implement the minimal adapter helpers**

```python
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.models.intel import IntelItem, IntelSourceType


def build_item_id(source_id: str, canonical_key: str) -> str:
    return f"{source_id}:{canonical_key}"


def normalize_feed_entry(source, entry, collected_at: datetime) -> IntelItem:
    published_at = parsedate_to_datetime(entry["published"]) if entry.get("published") else collected_at
    link = entry["link"]
    return IntelItem(
        item_id=build_item_id(source.source_id, link),
        source_type=IntelSourceType.UNIVERSITY_SITE,
        source_name=source.source_name,
        title=entry["title"],
        summary_short=entry.get("summary", "")[:80] or entry["title"],
        summary_long=entry.get("summary", "")[:180] or entry["title"],
        published_at=published_at.astimezone(timezone.utc),
        collected_at=collected_at,
        original_url=link,
        school_name=source.school_name,
        source_group=source.source_group,
        external_id=entry.get("id"),
    )


def parse_oxford_listing(source, html: str, collected_at: datetime) -> list[IntelItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[IntelItem] = []
    for article in soup.select("article"):
        link_node = article.select_one("h3 a")
        if link_node is None:
            continue
        link = urljoin(str(source.listing_url), link_node["href"])
        summary = article.select_one("p")
        time_node = article.select_one("time")
        published_at = (
            datetime.fromisoformat(time_node["datetime"])
            if time_node and time_node.get("datetime")
            else collected_at
        )
        items.append(
            IntelItem(
                item_id=build_item_id(source.source_id, link),
                source_type=IntelSourceType.UNIVERSITY_SITE,
                source_name=source.source_name,
                title=link_node.get_text(strip=True),
                summary_short=summary.get_text(strip=True)[:80] if summary else link_node.get_text(strip=True),
                summary_long=summary.get_text(strip=True)[:180] if summary else link_node.get_text(strip=True),
                published_at=published_at,
                collected_at=collected_at,
                original_url=link,
                school_name=source.school_name,
                source_group=source.source_group,
            )
        )
    return items
```

- [ ] **Step 5: Re-run the adapter tests and make them pass**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/collectors/test_university_news.py -v`

Expected: PASS with parser and normalization coverage green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/models/intel.py \
  backend/src/collectors/university_news.py \
  backend/tests/collectors/test_university_news.py
git commit -m "feat: add university news adapters"
```

### Task 3: Persist university items into `intel_items`

**Files:**
- Create: `backend/src/services/intel_ingest.py`
- Test: `backend/tests/services/test_intel_ingest.py`

- [ ] **Step 1: Write the failing ingest test**

```python
from datetime import datetime, timezone

import pytest

from src.models.intel import IntelItem, IntelSourceType
from src.services.intel_ingest import upsert_intel_items


class _FakeCollection:
    def __init__(self) -> None:
        self.calls = []

    async def update_one(self, query, update, upsert):
        self.calls.append((query, update, upsert))


@pytest.mark.asyncio
async def test_upsert_intel_items_uses_item_id_as_key():
    collection = _FakeCollection()
    items = [
        IntelItem(
            item_id="cambridge-news:https://example.com/story",
            source_type=IntelSourceType.UNIVERSITY_SITE,
            source_name="Cambridge News",
            title="Story",
            summary_short="Story",
            summary_long="Story",
            published_at=datetime(2026, 5, 21, 8, 0, tzinfo=timezone.utc),
            collected_at=datetime(2026, 5, 21, 8, 5, tzinfo=timezone.utc),
            original_url="https://example.com/story",
            school_name="Cambridge",
            source_group="重点学校",
        )
    ]

    await upsert_intel_items(collection, items)

    assert collection.calls[0][0] == {"item_id": items[0].item_id}
    assert collection.calls[0][2] is True
```

- [ ] **Step 2: Run the ingest test to verify it fails**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/services/test_intel_ingest.py -v`

Expected: FAIL because `upsert_intel_items` does not exist.

- [ ] **Step 3: Implement minimal persistence and source sync orchestration**

```python
from collections.abc import Iterable

from src.db.mongodb import mongodb


async def upsert_intel_items(collection, items: Iterable) -> int:
    count = 0
    for item in items:
        await collection.update_one(
            {"item_id": item.item_id},
            {"$set": item.model_dump(mode="json")},
            upsert=True,
        )
        count += 1
    return count


async def persist_university_items(items):
    collection = mongodb.get_collection("intel_items")
    return await upsert_intel_items(collection, items)
```

- [ ] **Step 4: Re-run the ingest tests**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/services/test_intel_ingest.py -v`

Expected: PASS with `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/intel_ingest.py \
  backend/tests/services/test_intel_ingest.py
git commit -m "feat: persist university intel items"
```

### Task 4: Read live university items through intel services and API

**Files:**
- Modify: `backend/src/services/intel_feed.py`
- Modify: `backend/src/api/intel.py`
- Modify: `backend/tests/services/test_intel_feed.py`
- Modify: `backend/tests/api/test_intel_api.py`

- [ ] **Step 1: Write failing tests for live-university reads**

```python
import pytest

from src.services import intel_feed


@pytest.mark.asyncio
async def test_load_university_items_reads_intel_collection(monkeypatch):
    row = {
        "item_id": "oxford-news:https://example.com/story",
        "source_type": "university_site",
        "source_name": "Oxford News",
        "title": "Oxford story",
        "summary_short": "Oxford story",
        "summary_long": "Oxford story",
        "impact_targets": [],
        "published_at": "2026-05-21T08:00:00Z",
        "collected_at": "2026-05-21T08:05:00Z",
        "original_url": "https://example.com/story",
        "school_name": "Oxford",
        "source_group": "重点学校",
    }

    monkeypatch.setattr(
        intel_feed.mongodb,
        "get_collection",
        lambda _name: _FakeCollection([row]),
    )

    items = await intel_feed.load_live_source_items("university_site", limit=10)

    assert len(items) == 1
    assert items[0].school_name == "Oxford"
```

- [ ] **Step 2: Run the service and API tests to verify they fail**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/services/test_intel_feed.py tests/api/test_intel_api.py -v`

Expected: FAIL because `load_live_source_items` does not exist and API still reads fixture-only paths.

- [ ] **Step 3: Implement live-source loading and fallback**

```python
async def load_live_source_items(source_key: str, limit: int = 20) -> list[IntelItem]:
    try:
        collection = mongodb.get_collection("intel_items")
    except RuntimeError:
        return []

    cursor = (
        collection.find({"source_type": source_key})
        .sort("published_at", -1)
        .limit(limit)
    )
    rows = await cursor.to_list(length=limit)
    return [IntelItem(**row) for row in rows]


async def build_overview_feed(seed_path: Path, live_limit: int = 20) -> list[IntelItem]:
    fixture_items = load_fixture_items(seed_path)
    live_xhs_items = await load_xiaohongshu_items(limit=live_limit)
    live_university_items = await load_live_source_items("university_site", limit=live_limit)

    filtered_fixture_items = [
        item
        for item in fixture_items
        if item.source_type not in {IntelSourceType.XIAOHONGSHU, IntelSourceType.UNIVERSITY_SITE}
    ]

    items = filtered_fixture_items[:]
    items[:0] = live_university_items or build_source_feed(fixture_items, "university_site")
    items[:0] = live_xhs_items or build_source_feed(fixture_items, "xiaohongshu")
    return items
```

- [ ] **Step 4: Update the API source handler**

```python
@router.get("/sources/{source_key}")
async def get_source_feed(source_key: str):
    if source_key not in VALID_SOURCE_KEYS:
        raise HTTPException(status_code=404, detail="来源不存在")

    if source_key == "xiaohongshu":
        items = await load_xiaohongshu_items()
    else:
        items = await load_live_source_items(source_key)

    if not items:
        items = build_source_feed(load_fixture_items(SEED_PATH), source_key)

    return {
        "source_key": source_key,
        "items": [item.model_dump(mode="json") for item in items],
        "helper_rail": build_helper_rail(items).model_dump(mode="json"),
    }
```

- [ ] **Step 5: Re-run the service and API tests**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/services/test_intel_feed.py tests/api/test_intel_api.py -v`

Expected: PASS with live-university reads verified and fixture fallback still green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/intel_feed.py \
  backend/src/api/intel.py \
  backend/tests/services/test_intel_feed.py \
  backend/tests/api/test_intel_api.py
git commit -m "feat: serve live university intel data"
```

### Task 5: Add a one-shot collection entrypoint for the first slice

**Files:**
- Modify: `backend/src/collectors/university_news.py`
- Modify: `backend/tests/collectors/test_university_news.py`

- [ ] **Step 1: Write the failing orchestration test**

```python
import pytest

from src.collectors.university_news import collect_all_university_news


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
    assert len(calls) == 4
```

- [ ] **Step 2: Run the orchestration test to verify it fails**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/collectors/test_university_news.py::test_collect_all_university_news_skips_disabled_sources -v`

Expected: FAIL because the orchestration helper does not exist.

- [ ] **Step 3: Implement the minimal source loop**

```python
async def collect_source_items(session, source):
    if source.adapter_type == "feed":
        return await collect_feed_items(session, source)
    return await collect_listing_items(session, source)


async def collect_all_university_news(session):
    items = []
    for source in UNIVERSITY_SOURCES:
        if not source.enabled:
            continue
        items.extend(await collect_source_items(session, source))
    return items
```

- [ ] **Step 4: Re-run the orchestration test**

Run: `cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/collectors/test_university_news.py::test_collect_all_university_news_skips_disabled_sources -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/collectors/university_news.py \
  backend/tests/collectors/test_university_news.py
git commit -m "feat: add university news collection entrypoint"
```

## Self-Review

- Spec coverage:
  - First-wave schools covered by Task 1 source registry.
  - `feed` and `listing` adapter split covered by Task 2 and Task 5.
  - MongoDB upsert into `intel_items` covered by Task 3.
  - `/api/intel/*` live-data integration covered by Task 4.
  - Browser fallback, summary generation, and RSS export remain intentionally out of scope.
- Placeholder scan:
  - No `TODO`, `TBD`, or implicit “handle later” steps remain.
- Type consistency:
  - Plan consistently uses `UniversitySource`, `IntelItem`, `collect_source_items`, `load_live_source_items`, and `upsert_intel_items`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-21-university-news-feed-ingestion.md`.

Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

This thread will use **Inline Execution**, because the user has already approved the architecture and asked to proceed immediately in the same session.
