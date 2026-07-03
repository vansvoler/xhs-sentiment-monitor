# 信源适配器重构 + UCAS 配置化设计

## 背景

当前信源抓取链路存在以下结构性缺陷：

1. `collectors/university_news.py` 通过 URL 字符串 `"search.json" in url` 和
   `"articles.json" in url` 来判定 UCL Funnelback / Imperial 私有 JSON 协议，
   一旦上游改 URL 路径会静默失效。
2. UCAS（`collectors/ucas_news.py`）独立硬编码 URL 和 parser，没有走 `IntelSource`
   配置化体系，调度器为它单独保留一个 cron job。
3. 适配器分发逻辑散落在 `collect_feed_items` / `collect_listing_items` /
   `collect_source_items` 三个函数中，新增适配器（rsshub、playwright、wechat 等）
   会让这一层继续膨胀。
4. `intel_source_probe.py` 不能识别 UCL / Imperial 私有 JSON 结构，对应站点的
   "添加信源" 用户路径会被推荐成普通 feed 而失败。

## 目标

把"如何抓"集中到一组显式的 adapter 类，让：

- 配置 → adapter 的对应关系只看 `source.adapter_type`，不再用 URL 字符串 hack。
- 现有所有信源（含 ucl-news、imperial-news、oxford-news、UCAS）都能用同一套配置
  schema 描述并经同一个调度入口 fan-out。
- 新增适配器（后续 phase 的 rsshub、playwright）只需要新增一个文件 + 注册一行。
- 前端 / 配置文件 / DB 现存数据不被破坏（兼容旧 `adapter_type` 字面量）。
- probe 能识别更多协议形态，给"添加信源"端到端流程提供准确推荐。

## 非目标

- 不在本期引入 RSSHub / Playwright / 并发抓取 / bulk_write / ETag（属于后续
  Phase D、E）。
- 不修改 `services/intel_feed.py` 里给小红书 Note 用的 `infer_impact_targets`
  （另一域，规则不同）。
- 不修改前端 add-source-dialog 表单交互，仅扩展 IntelAdapterType 字面量集和
  下拉项。

## 适配器枚举

新的 `AdapterType` 字面量集（向后兼容，旧值全部保留）：

| adapter_type | 来源 | 说明 |
|---|---|---|
| `feed` | 旧 | 通用 RSS / Atom，feedparser 解析 |
| `rss` | 旧 | `feed` 的别名 |
| `json_feed` | 旧 | 保留兼容位，当前实现等价于 `feed`（feedparser 兜底） |
| `listing` | 旧 | 保留 Oxford 的历史 adapter_type，运行时等价于 `html_listing` |
| `html_listing` | 旧 | 配置化 CSS selector |
| `ucl_json` | **新** | UCL Funnelback search API（专属 JSON 结构） |
| `imperial_json` | **新** | Imperial articles.json（专属 JSON 结构） |
| `ucas_html` | **新** | UCAS Latest news 区块解析（接管原 `collectors/ucas_news.py`） |

Phase D/E 在此基础上追加 `rsshub` / `playwright`。

## 模块结构

```
backend/src/collectors/
  adapters/
    __init__.py        — ADAPTER_REGISTRY: dict[str, type[BaseAdapter]]
    base.py            — BaseAdapter ABC
    feed.py            — FeedAdapter（feed/rss/json_feed → feedparser）
    html_listing.py    — HtmlListingAdapter（html_listing；listing 别名走 Oxford 分支）
    ucl_json.py        — UCLJsonAdapter
    imperial_json.py   — ImperialJsonAdapter
    ucas_html.py       — UcasHtmlAdapter
  university_news.py   — 保留通用工具（_coerce_datetime、_build_item、Cloudflare 检测），
                          collect_source_items 改为 ADAPTER_REGISTRY 分发
  ucas_news.py         — 改为薄壳：DEFAULT_REQUEST_HEADERS + parse_ucas_latest_news 移到
                          adapters/ucas_html.py；保留旧接口（collect_ucas_news /
                          collect_ucas_news_with_report）作为 backward-compat 桥接，
                          内部委托给 UcasHtmlAdapter 以便老 scheduler job 删除后无意外
```

## BaseAdapter 协议

```python
class BaseAdapter(ABC):
    @abstractmethod
    async def fetch(
        self,
        session: aiohttp.ClientSession,
        source: IntelSource,
    ) -> list[IntelItem]:
        ...
```

`SourceBlockedError` 由 adapter 内部抛出，外层调度统一捕获。

## 配置迁移

`backend/config/intel_sources.json` 一次性迁移：

| source_id | 旧 adapter_type | 新 adapter_type | 备注 |
|---|---|---|---|
| oxford-news | listing | listing | 保持别名，HtmlListingAdapter 在 `selectors is None` 时回退 Oxford 分支（暂不强制写 selectors，下个版本再彻底统一） |
| cambridge-news | feed | feed | 无变化 |
| ucl-news | feed | **ucl_json** | 删除 URL 字符串 hack |
| imperial-news | feed | **imperial_json** | 删除 URL 字符串 hack |
| cambridgeinternational-org-news | html_listing | html_listing | 无变化 |
| oxfordaqa-com-news | feed | feed | 无变化 |
| **ucas-news（新增）** | — | **ucas_html** | 由 UCAS 硬编码源迁入配置 |

UCAS 配置：

```json
{
  "source_id": "ucas-news",
  "source_type": "ucas",
  "source_name": "UCAS",
  "source_group": "UCAS",
  "adapter_type": "ucas_html",
  "listing_url": "https://www.ucas.com/about-us/news-and-insights",
  "enabled": true
}
```

## UCAS 接入策略

阶段性双轨：

1. 配置文件加入 ucas-news 记录，scheduler 通过统一 `collect_university_news_job`
   把它和大学官网一起抓。
2. 仍保留 `scheduler.collect_ucas_news_job` 入口、`intel_ingest.sync_ucas_news`、
   `collect_ucas_news_with_report` 三个旧接口，避免影响 `scripts/collect_ucas_news.sh`、
   `run_ucas_news_sync_job` 等外部使用方。这两条链路调用同一个 UcasHtmlAdapter，
   结果一致，仅是入口冗余。
3. 下个版本（Phase C2）评估"双跑"对成本的影响后再决定移除哪条。

Scheduler `add_job` 不立刻删除 `collect_ucas_news` job。

## API 校验

`api/intel.py:_validate_source_config` 改成 schema 驱动：

```python
ADAPTER_REQUIRED_FIELDS: dict[str, list[Literal["feed_url", "listing_url", "selectors"]]] = {
    "feed":           ["feed_url"],
    "rss":            ["feed_url"],
    "json_feed":      ["feed_url"],
    "ucl_json":       ["feed_url"],
    "imperial_json":  ["feed_url"],
    "listing":        ["listing_url"],
    "html_listing":   ["listing_url", "selectors"],
    "ucas_html":      ["listing_url"],
}
```

每个新增 adapter 在表里登记必填字段；校验失败按 422 返回。

## Probe 升级

`intel_source_probe.py` 新增两条识别分支：

1. 抓到 JSON 且 payload 顶层有 `results` 或 `response.resultPacket.results` →
   推荐 `ucl_json`。
2. 抓到 JSON 且 payload 顶层有 `articles` 列表（每条带 `articleURL`）→
   推荐 `imperial_json`。

这两个识别放在 `_fetch_text` 拿到 `content_type` 是 `application/json` 之后、
fallback 到 HTML 路径之前。

UCAS 探测暂不做（UCAS 不通过 probe 入口添加，是硬编码 seed）。

## 前端契约改动

`frontend/src/types/intel.ts`：

```ts
export type IntelAdapterType =
  | "feed" | "rss" | "json_feed"
  | "listing" | "html_listing"
  | "ucl_json" | "imperial_json"
  | "ucas_html";
```

`add-source-dialog.tsx` 表单中的 adapter_type 下拉枚举跟随扩展。
ucl_json / imperial_json / ucas_html 视为"系统内置"，UI 不暴露给用户手选——只在
probe 推荐时由后端回填。下拉只展示 `feed` / `rss` / `html_listing` / `listing`。

## 数据模型

`IntelSource` schema 无需新增字段。`IntelItem` / `IntelSourceSyncReport` 无变化
（`notes` 字段已在 Phase A4 加入）。

`models/intel.IntelSourceType` 无变化（UCAS 已有 `UCAS = "ucas"` 枚举值）。

## 测试改动

新增：

- `tests/collectors/adapters/test_feed_adapter.py` ← 从 test_university_news 拆
- `tests/collectors/adapters/test_html_listing_adapter.py` ← 拆 Oxford / 配置化两条
- `tests/collectors/adapters/test_ucl_json_adapter.py`
- `tests/collectors/adapters/test_imperial_json_adapter.py`
- `tests/collectors/adapters/test_ucas_html_adapter.py` ← 从 test_ucas_news 搬过来
- `tests/collectors/test_adapter_registry.py` ← 注册表完备性

修改：

- `tests/collectors/test_university_news.py`：保留 `collect_all_university_news_with_reports`
  分发流程相关用例；删除 URL hack 相关分支测试（已无对应代码）。
- `tests/api/test_intel_api.py`：补一个 ucl_json / imperial_json 不需要 selectors
  的校验通过用例。
- `tests/collectors/test_intel_source_probe.py`：补 UCL / Imperial JSON 推断用例。
- `tests/collectors/test_university_sources.py`：迁移后的 ucl-news / imperial-news /
  ucas-news 期望值更新。

## 风险与回滚

| 风险 | 缓解 |
|---|---|
| 迁移 `ucl-news` adapter_type 但 UCL Funnelback 上线改了响应结构 | UCLJsonAdapter 与现有 `normalize_ucl_result` 行为等价，等价替换 |
| Oxford 站点 selectors 没在本期统一，listing 别名保留特例分支 | HtmlListingAdapter 显式注释 `# legacy: Oxford specific`，下期拆 |
| UCAS 双跑导致每小时多一次 HTTP | UCAS 站不计费，可接受；移除时机由 Phase C2 把关 |
| 前端旧客户端仍发 adapter_type=`feed` 给 UCL/Imperial 类 URL | 后端 probe 返回新的 ucl_json/imperial_json，老客户端读到该值仅用于展示，写回时若仍传 `feed` 也合法（FeedAdapter 仍能工作），降级而非破坏 |

## 不在范围

- 并发 fan-out（Phase D1）
- bulk_write（Phase D2）
- intel_source_syncs append-only（Phase D3）
- ETag/304（Phase D4）
- 微信公众号 / RSSHub / Playwright（Phase E）
- 调度频率配置化（独立任务）
