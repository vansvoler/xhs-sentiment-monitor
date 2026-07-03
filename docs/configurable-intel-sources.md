# 可配置官网信源

官网/机构网站信源统一写在：

`backend/config/intel_sources.json`

后端启动后，调度器会按现有“大学新闻同步”任务周期读取这些来源，写入 `intel_items`，同步状态写入 `intel_source_syncs`。

## 自动探测

添加新网站前，先在 `backend/` 目录运行：

```bash
bash scripts/probe_intel_source.sh "https://example.com/news" \
  --source-type visa_policy \
  --source-name "Example News" \
  --source-group "签证政策"
```

脚本会输出：

- `status`: `success` / `blocked` / `unsupported`
- `message`: 推荐理由或失败原因
- `sample_count`: feed 能解析出的样本条数
- `recommended_config`: 可复制进 `backend/config/intel_sources.json` 的配置

探测优先级：

1. URL 本身是否为 RSS / Atom feed
2. 页面 `<link rel="alternate">` 是否声明 RSS / Atom
3. 常见 feed 地址，如 `/feed`、`/rss`、`/feed.xml`
4. 静态 HTML 新闻列表结构
5. 反爬/无法识别则输出 `blocked` 或 `unsupported`

本地改完配置后，可以重启后端，或在 `backend/` 目录手动跑一次：

```bash
bash scripts/collect_university_news.sh
```

## 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `source_id` | 是 | 全局唯一 ID，建议用小写短横线 |
| `source_type` | 是 | `university_site` / `exam_board` / `visa_policy` / `wechat_media` / `ucas` |
| `source_name` | 是 | 前端展示名 |
| `source_group` | 是 | 分组名，如 `重点学校`、`签证政策` |
| `school_name` | 否 | 学校名；非学校网站可不填 |
| `adapter_type` | 是 | `feed`、`rss`、`json_feed`、`listing`、`html_listing` |
| `feed_url` | feed 类必填 | RSS / Atom / 已适配 JSON feed 地址 |
| `listing_url` | HTML 类必填 | HTML 列表页地址 |
| `selectors` | `html_listing` 必填 | CSS selector 解析规则 |
| `enabled` | 否 | 默认 `true` |

## RSS / Atom 示例

```json
{
  "source_id": "cambridge-news",
  "source_type": "university_site",
  "school_name": "Cambridge",
  "adapter_type": "feed",
  "source_group": "重点学校",
  "source_name": "Cambridge News",
  "feed_url": "https://www.cam.ac.uk/news/feed"
}
```

## HTML 列表页示例

```json
{
  "source_id": "ukvi-news",
  "source_type": "visa_policy",
  "source_name": "UKVI News",
  "source_group": "签证政策",
  "adapter_type": "html_listing",
  "listing_url": "https://www.gov.uk/search/news-and-communications",
  "selectors": {
    "item": "article",
    "title": "h2 a",
    "url": "h2 a",
    "summary": "p",
    "date": "time"
  }
}
```

`date` 会优先读取节点的 `datetime` 属性；如果没有日期，系统会用本次采集时间。

## 当前限制

- `html_listing` 只支持静态 HTML，不执行 JavaScript。
- Cloudflare、登录墙、强反爬网站会记录为失败或被拦截。
- 任意 JSON 结构暂未做通用路径映射；当前 JSON feed 主要兼容 UCL 和 Imperial 这类已适配结构。
