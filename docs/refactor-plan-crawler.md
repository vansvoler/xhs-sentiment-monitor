# 后端信源抓取重构计划

> 目标：将信源抓取覆盖率从当前的约 55% 提升至 90%+，同时消除现有结构性缺陷。

---

## 背景与现状问题

### 现有架构

```
intel_sources.json
  └─ UNIVERSITY_SOURCES (模块级静态变量，进程启动时加载一次)
       └─ scheduler → collect_university_news_job (每 60 分钟)
            └─ collect_all_university_news_with_reports
                 └─ for source in UNIVERSITY_SOURCES:   ← 串行
                      collect_source_items(session, source)
                        ├─ feed/rss/json_feed → collect_feed_items
                        │     └─ "search.json" in url? → UCL JSON 解析
                        │        "articles.json" in url? → Imperial JSON 解析
                        │        else → feedparser
                        ├─ listing → parse_oxford_listing (Oxford 专属)
                        └─ html_listing → parse_configured_html_listing
                 └─ upsert_intel_items (逐条 update_one)
```

### 已确认的结构性问题

| # | 问题 | 影响范围 |
|---|------|---------|
| 1 | `UNIVERSITY_SOURCES` 是模块级静态变量，新增信源不重启不生效 | Bug，所有动态添加的信源 |
| 2 | 适配器分发用 URL 字符串匹配（`"search.json" in url`），URL 变化静默失效 | UCL、Imperial |
| 3 | JS 渲染页面：`aiohttp` 拿到空壳 HTML，`item_count=0` 但状态记 SUCCESS | 所有 SPA 类大学官网 |
| 4 | `wechat_media` 类型：枚举和导航项存在，采集代码完全缺失 | 所有微信公众号信源 |
| 5 | 串行抓取：N 个信源 = N 次串行 HTTP，单轮同步 O(N) 时间 | 所有信源 |
| 6 | 逐条 MongoDB upsert：N 条 item = N 次 RTT | 所有信源 |
| 7 | 无 ETag/304 增量机制，每次全量重抓再全量 upsert | 所有信源 |
| 8 | `infer_impact_targets` 在三个文件中各写一遍，逻辑不一致 | 维护性 |

---

## 目标架构

```
intel_sources.json
  └─ load_intel_sources() 每次调度时动态读取（不再静态缓存）
       └─ scheduler → collect_university_news_job
            └─ asyncio.gather(semaphore=5) 并发抓取
                 └─ ADAPTER_REGISTRY[source.adapter_type]().fetch()
                      ├─ FeedAdapter      → feedparser（原生 RSS/Atom）
                      ├─ RSSHubAdapter    → 拼 RSSHub URL → feedparser
                      ├─ PlaywrightAdapter→ 无头浏览器渲染 → BeautifulSoup
                      ├─ HtmlListingAdapter → 现有 CSS selector 逻辑
                      ├─ UCLJsonAdapter   → UCL Funnelback JSON
                      └─ ImperialJsonAdapter → Imperial JSON
            └─ bulk_write 批量 upsert
```

---

## 分阶段实施计划

### Phase 0：修复 Bug（不影响其他 Phase，应立即执行）

**改动文件**：`backend/src/collectors/scheduler.py`

**问题**：`UNIVERSITY_SOURCES` 是模块级静态变量，通过 `POST /api/intel/sources` 新增信源后，下一轮定时任务仍使用旧列表，新信源不会被自动同步。

**修改**：在 `collect_university_news_job` 内每次动态调用 `load_intel_sources()`：

```python
# 修改前
async def collect_university_news_job() -> None:
    count = await sync_university_news()  # 内部使用 UNIVERSITY_SOURCES 静态变量

# 修改后
from src.collectors.university_sources import load_intel_sources

async def collect_university_news_job() -> None:
    sources = load_intel_sources()  # 每次从文件读取，感知新增信源
    items, reports = await collect_all_university_news_with_reports(session, sources)
    ...
```

同时修改 `collect_all_university_news_with_reports` 签名，接受外部传入的 `sources` 列表。

---

### Phase 1：适配器插件化

**目的**：消除 URL 字符串 hack，建立可扩展的适配器体系。

**新增文件**：`backend/src/collectors/adapters/`

```
adapters/
  __init__.py         ← 导出 ADAPTER_REGISTRY
  base.py             ← BaseAdapter 抽象类
  feed.py             ← FeedAdapter（合并现有 collect_feed_items）
  html_listing.py     ← HtmlListingAdapter（合并现有两个 HTML 解析函数）
  ucl_json.py         ← UCLJsonAdapter（从 university_news.py 拆出）
  imperial_json.py    ← ImperialJsonAdapter（从 university_news.py 拆出）
```

**`base.py`**：

```python
from abc import ABC, abstractmethod
from src.collectors.university_sources import IntelSource
from src.models.intel import IntelItem

class BaseAdapter(ABC):
    @abstractmethod
    async def fetch(self, session, source: IntelSource) -> list[IntelItem]:
        ...
```

**`__init__.py`**：

```python
from .feed import FeedAdapter
from .html_listing import HtmlListingAdapter
from .ucl_json import UCLJsonAdapter
from .imperial_json import ImperialJsonAdapter

ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "feed":           FeedAdapter,
    "rss":            FeedAdapter,
    "html_listing":   HtmlListingAdapter,
    "listing":        HtmlListingAdapter,   # 兼容现有 Oxford 配置
    "json_ucl":       UCLJsonAdapter,
    "json_imperial":  ImperialJsonAdapter,
}
```

**修改 `university_news.py`**：

```python
# collect_source_items 简化为两行
async def collect_source_items(session, source: IntelSource) -> list[IntelItem]:
    from src.collectors.adapters import ADAPTER_REGISTRY
    adapter = ADAPTER_REGISTRY.get(source.adapter_type)
    if adapter is None:
        raise ValueError(f"未知适配器类型: {source.adapter_type}")
    return await adapter().fetch(session, source)
```

**`IntelSource` 配置扩展**（`university_sources.py`）：

```python
AdapterType = Literal[
    "feed", "rss",                    # 原生 RSS/Atom
    "html_listing", "listing",        # 静态 HTML，listing 为历史兼容名
    "json_ucl", "json_imperial",      # 私有 JSON API
    "rsshub",                         # Phase 2 新增
    "playwright",                     # Phase 3 新增
]
```

**迁移现有 Oxford 配置**：Oxford 目前 `adapter_type="listing"` 用专属解析函数，改为 `adapter_type="html_listing"` + 自动 selector 推断，或者保留 `listing` 作为 `HtmlListingAdapter` 的别名（向后兼容）。

**合并重复逻辑**：把三处 `infer_impact_targets` 合并到 `backend/src/utils/intel_utils.py`，统一用含英文关键词的完整版本。

---

### Phase 2：集成 RSSHub（解决微信公众号 + 部分 JS 站）

**目的**：一行配置接入微信公众号及 RSSHub 已支持的 700+ 网站路由。

#### 2.1 部署 RSSHub

在项目根目录 `docker-compose.yml` 新增：

```yaml
rsshub:
  image: diygod/rsshub:latest
  restart: unless-stopped
  ports:
    - "1200:1200"
  environment:
    CACHE_TYPE: memory
    CACHE_EXPIRE: 600       # 缓存 10 分钟，避免重复抓取
    TITLE_LENGTH_LIMIT: 200
```

#### 2.2 后端配置

`backend/src/config.py` 新增：

```python
RSSHUB_BASE_URL: str = "http://localhost:1200"
```

#### 2.3 IntelSource 新增字段

```python
class IntelSource(BaseModel):
    ...
    rsshub_route: str | None = None   # 如 "/wechat/mp/article/MzI4MDU4OTYy"
```

#### 2.4 RSSHubAdapter

新增 `adapters/rsshub.py`：

```python
class RSSHubAdapter(BaseAdapter):
    async def fetch(self, session, source: IntelSource) -> list[IntelItem]:
        if not source.rsshub_route:
            raise ValueError(f"{source.source_id} 缺少 rsshub_route")
        url = f"{settings.RSSHUB_BASE_URL}{source.rsshub_route}"
        # 复用 FeedAdapter，只替换 URL
        proxy_source = source.model_copy(update={"feed_url": url, "adapter_type": "feed"})
        return await FeedAdapter().fetch(session, proxy_source)
```

#### 2.5 微信公众号信源配置示例

`intel_sources.json` 新增：

```json
{
  "source_id": "wechat-xxx",
  "source_type": "wechat_media",
  "source_name": "XXX公众号",
  "adapter_type": "rsshub",
  "rsshub_route": "/wechat/mp/article/{biz_id}",
  "source_group": "媒体公众号",
  "enabled": true
}
```

获取 `biz_id` 方法：复制任意一篇公众号文章链接，URL 中 `__biz=` 参数后的值即为 `biz_id`。

#### 2.6 ADAPTER_REGISTRY 更新

```python
from .rsshub import RSSHubAdapter

ADAPTER_REGISTRY["rsshub"] = RSSHubAdapter
```

---

### Phase 3：Playwright 适配器（解决 JS 渲染）

**目的**：覆盖无原生 RSS、页面内容由 JavaScript 渲染的现代大学官网。

#### 3.1 依赖

```toml
# backend/pyproject.toml 新增
playwright = ">=1.40"
```

安装浏览器：`playwright install chromium --with-deps`

#### 3.2 IntelSource 新增字段

```python
class IntelSource(BaseModel):
    ...
    playwright_wait_selector: str | None = None  # 等待某元素出现后再提取 HTML
    # 示例："article.news-item" 表示等新闻条目渲染完成
```

#### 3.3 PlaywrightAdapter

新增 `adapters/playwright_adapter.py`：

```python
from playwright.async_api import async_playwright

class PlaywrightAdapter(BaseAdapter):
    async def fetch(self, session, source: IntelSource) -> list[IntelItem]:
        url = str(source.listing_url)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            if source.playwright_wait_selector:
                await page.wait_for_selector(
                    source.playwright_wait_selector, timeout=10000
                )
            html = await page.content()
            await browser.close()

        collected_at = datetime.now(timezone.utc)
        if source.selectors:
            return parse_configured_html_listing(source, html, collected_at)
        # 无 selector 则尝试自动推断（复用 probe 逻辑）
        selectors = infer_html_listing_selectors(html)
        if selectors is None:
            return []
        source_with_selectors = source.model_copy(update={"selectors": selectors})
        return parse_configured_html_listing(source_with_selectors, html, collected_at)
```

**注意**：Playwright 比 aiohttp 慢 5-10 倍，并发 semaphore 中对 Playwright 信源限制为 2-3 个并发。

#### 3.4 探测器升级

`intel_source_probe.py` 新增自动降级逻辑：

```python
async def probe_intel_source(session, url, ...) -> ProbeResult:
    text, content_type = await _fetch_text(session, url)

    # ... 现有逻辑 ...

    # 新增：aiohttp 拿到空结果，怀疑 JS 渲染，用 Playwright 重试
    if not items and "html" in content_type.lower():
        try:
            html = await _playwright_fetch(url)
            selectors = infer_html_listing_selectors(html)
            if selectors:
                return ProbeResult(
                    status="success",
                    message="JS 渲染页面，已用 Playwright 识别 selector。",
                    recommended_source=IntelSource(
                        ...,
                        adapter_type="playwright",
                        selectors=selectors,
                    ),
                )
        except Exception:
            pass  # Playwright 也失败则继续走 unsupported
```

---

### Phase 4：性能优化

**目的**：消除串行抓取和逐条 upsert 的性能瓶颈。

#### 4.1 并发抓取

修改 `collect_all_university_news_with_reports`：

```python
import asyncio

async def collect_all_university_news_with_reports(
    session, sources: list[IntelSource]
) -> tuple[list[IntelItem], list[IntelSourceSyncReport]]:
    sem = asyncio.Semaphore(5)  # 最多 5 个并发，对 Playwright 信源单独限制为 2

    async def fetch_one(source):
        async with sem:
            try:
                items = await collect_source_items(session, source)
                return items, IntelSourceSyncReport(status=SUCCESS, ...)
            except SourceBlockedError as e:
                return [], IntelSourceSyncReport(status=BLOCKED, ...)
            except Exception as e:
                return [], IntelSourceSyncReport(status=ERROR, ...)

    results = await asyncio.gather(*[fetch_one(s) for s in sources if s.enabled])
    items = [item for items, _ in results for item in items]
    reports = [report for _, report in results]
    return items, reports
```

#### 4.2 批量 upsert

修改 `intel_ingest.py`：

```python
from pymongo import UpdateOne

async def upsert_intel_items(collection, items: Iterable[IntelItem]) -> int:
    item_list = list(items)
    if not item_list:
        return 0
    ops = [
        UpdateOne(
            {"item_id": item.item_id},
            {"$set": item.model_dump(mode="json")},
            upsert=True,
        )
        for item in item_list
    ]
    result = await collection.bulk_write(ops, ordered=False)
    return result.upserted_count + result.modified_count
```

#### 4.3 ETag / 304 增量抓取

在 `intel_source_syncs` 集合中新增字段 `etag` 和 `last_modified`。

`FeedAdapter` 改造：

```python
class FeedAdapter(BaseAdapter):
    async def fetch(self, session, source: IntelSource) -> list[IntelItem]:
        # 读取上次 sync 的缓存头
        last_sync = await get_last_sync_meta(source.source_id)  # 新增辅助函数
        headers = {**DEFAULT_REQUEST_HEADERS}
        if last_sync.etag:
            headers["If-None-Match"] = last_sync.etag
        if last_sync.last_modified:
            headers["If-Modified-Since"] = last_sync.last_modified

        async with session.get(url, headers=headers) as response:
            if response.status == 304:
                return []  # 内容未变，直接跳过
            response.raise_for_status()
            # 保存新的缓存头
            await save_sync_meta(source.source_id, response.headers)
            text = await response.text()

        return parse_feed(source, text)
```

---

## 文件改动汇总

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/src/collectors/scheduler.py` | 修改 | Phase 0：动态加载信源列表 |
| `backend/src/collectors/university_sources.py` | 修改 | Phase 1：扩展 AdapterType，新增 rsshub_route / playwright_wait_selector 字段 |
| `backend/src/collectors/university_news.py` | 修改 | Phase 1：collect_source_items 改为注册表分发，移除 URL 字符串 hack |
| `backend/src/collectors/adapters/__init__.py` | 新增 | Phase 1：ADAPTER_REGISTRY |
| `backend/src/collectors/adapters/base.py` | 新增 | Phase 1：BaseAdapter 抽象类 |
| `backend/src/collectors/adapters/feed.py` | 新增 | Phase 1：从 university_news.py 拆出 |
| `backend/src/collectors/adapters/html_listing.py` | 新增 | Phase 1：从 university_news.py 拆出 |
| `backend/src/collectors/adapters/ucl_json.py` | 新增 | Phase 1：从 university_news.py 拆出 |
| `backend/src/collectors/adapters/imperial_json.py` | 新增 | Phase 1：从 university_news.py 拆出 |
| `backend/src/collectors/adapters/rsshub.py` | 新增 | Phase 2：RSSHubAdapter |
| `backend/src/collectors/adapters/playwright_adapter.py` | 新增 | Phase 3：PlaywrightAdapter |
| `backend/src/collectors/intel_source_probe.py` | 修改 | Phase 3：探测失败时 Playwright 自动降级 |
| `backend/src/services/intel_ingest.py` | 修改 | Phase 4：bulk_write，ETag 逻辑 |
| `backend/src/utils/intel_utils.py` | 新增 | Phase 1：合并三处 infer_impact_targets |
| `backend/src/config.py` | 修改 | Phase 2：新增 RSSHUB_BASE_URL |
| `backend/pyproject.toml` | 修改 | Phase 3：新增 playwright 依赖 |
| `docker-compose.yml` | 修改 | Phase 2：新增 rsshub service |
| `backend/config/intel_sources.json` | 修改 | Phase 2：新增微信公众号信源示例 |

---

## 预期覆盖率

| 适配器 | 覆盖场景 | 覆盖率贡献 |
|--------|---------|-----------|
| FeedAdapter（原生 RSS） | 英国主要大学、GOV.UK、考试局 | ~55% |
| RSSHubAdapter | 微信公众号、有 RSSHub 路由的媒体站 | +15% |
| PlaywrightAdapter | JS 渲染的现代大学官网 | +15% |
| HtmlListingAdapter | 静态 HTML 列表页 | +10% |
| 硬失败（需登录、强反爬） | — | ~5% |
| **合计** | | **~95%** |

---

## 各 Phase 优先级与工作量估算

| Phase | 优先级 | 估算工作量 | 解决的核心问题 |
|-------|--------|-----------|--------------|
| Phase 0 | 立刻 | 0.5h | 新增信源不重启不生效的 Bug |
| Phase 1 | 高 | 3-4h | 适配器可扩展性，消除 URL hack |
| Phase 2 | 高 | 1-2h | 微信公众号完全空白 |
| Phase 3 | 中 | 3-4h | JS 渲染静默失败 |
| Phase 4 | 中 | 2-3h | 性能：并发 + bulk_write + ETag |

Phase 0 和 Phase 1 建议优先实施，Phase 2 的 RSSHub 部署成本极低（Docker 一行），可以和 Phase 1 一起做。
