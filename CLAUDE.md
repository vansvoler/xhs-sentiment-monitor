# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

全仓统一启停在仓库根目录执行：

```bash
# 同时启动前后端，日志写到根目录 logs/
bash scripts/dev-all.sh

# 本地联通 smoke test
bash scripts/smoke.sh
```

所有后端操作在 `backend/` 目录下执行：

```bash
# 初始化（首次，需 Python 3.11+）
cd backend && uv venv --python 3.11 && uv pip install -e ".[dev]"

# 开发启动
cd backend && ./scripts/dev.sh

# 冒烟测试单轮采集（不跑调度器）
cd backend && uv run python -m src.collectors.xhs_api 口红

# 代码检查
cd backend && uv run ruff check src/
cd backend && uv run mypy src/

# 测试
cd backend && uv run pytest
cd backend && uv run pytest tests/test_foo.py::test_bar
```

日志到 `backend/logs/`。

## 架构概览

**采集链路**：TikHub API（`api.tikhub.dev`）→ `TikHubClient` → `DataCollector` → MongoDB → LLM 情感+相关性分析 → WebSocket 推送

> 官方情报（UCAS/大学官网/考试局/签证）已拆分为独立项目 `study-abroad-intel`，本仓库只做小红书舆情。

### 模块关系

```
APScheduler (collectors/scheduler.py)
  daily_collect  每天北京时间 DAILY_COLLECT_HOUR(=8) 点一次，串行跑：
    ├─ 关键词采集 → 入库新笔记 → 广播
    ├─ analyze_sentiment  LLM 情感+relevance；判负即触发告警
    └─ scan_alerts        按关键词扫负面率/声量突增 → alerts
  启动补采：错过当天采集点且今天没采过才补一次（重启不重复扣费）
  collect_comments  已关停（小红书评论接口 $0.01/次太贵，ENABLE_COMMENT_COLLECTION=False）
         │
         ▼
  DataCollector (collectors/xhs_api.py) — 采集 + upsert
         │
         ▼
  TikHubClient (collectors/tikhub.py)
         │  search_notes 冷启动 400 时重试 3 次（2s/4s 递增）
         ▼
  XHSAdapter → _Http：主域名 api.tikhub.dev 失败切 api.tikhub.io
         │
         ▼
  https://api.tikhub.dev/api/v1/xiaohongshu/app_v2/...
```

### API 路由（挂在 `/api/` 前缀下）

`/notes` `/comments` `/sentiment` `/trends` `/competitors` `/alerts` `/kol` — 全部读 MongoDB。

> `/kol` KOL 挖掘：聚合 `notes` 作者 → 关联度/互动打分 → 候选池，**不设发文数门槛**（`min_notes=1`，单篇高互动作者是重要招募对象）。综合分 = 关联度 × 0.5 + 互动 × 0.5，**情感不入分**（正面率仅展示）。关联度 = 命中词类型分（brand 100 / competitor 75 / industry 55，取最靠近品牌的一类）× 发文深度增益（log 归一，满 10 篇拿满，单篇仍保 70% 基础分）。互动满分线 `_ENGAGEMENT_CEIL=1500`，取自库内 on_topic 作者篇均互动 P90（国际教育垂类头部线，别按全平台美妆量级设）。账号身份 `account_type` 按**昵称含机构名**判定（`own_matrix`/`competitor_matrix`/`individual`）——官号与员工号会把机构名写进昵称（`渊学通-常州`、`潘潘在唯寻`），高精度低召回；判不出一律 `individual`，**只打标、不降权、不隐藏**（签约关系无法从公开数据推断，不猜测；旧的"命中词全属竞品词即打竞品标并 ×0.2"会误杀只发过一篇竞品笔记的素人，已废除）。昵称规则仍会看走眼（如`聪聪-活力校长版`），故 `POST /kol/{uid}/account-type` 支持**人工校正，人工永远胜出**并在列表标「人工」；传空串撤销校正、交还自动规则。聚合只算当前 `monitor_keywords` 运行时词表下的笔记，历史孤儿词自动出局。前端默认只看素人 tab；行可展开看 `GET /kol/{uid}/notes`（该作者命中监控词的笔记，分数的原始依据），昵称直链小红书主页。人工态 `candidate`/`shortlisted`/`rejected`；**排除是隐藏不是删除**——默认视图（不传 `status`）只含前两者，已排除的在自己的 tab 里可随时恢复。自动规则再准也会放进同名异物捞来的无关号（如 `yxt` 命中的追星账号），排除是人工的最后一道闸。人工态与付费富化（`get_user_info` 补粉丝数，有每日上限+缓存）存 `kol_profiles`。设计见 `docs/kol-discovery-design.md`。

> 数据模型要点：笔记 `category` 只存桶值（brand/competitor/industry），真正的关键词在 `search_keyword`。竞品/趋势/告警一律按 `search_keyword` 聚合、用 `published_at`（发布时间）做时间轴，而非 `collected_at`（抓取时间）。同一篇笔记上游会返回变体 `note_id`，故按 `dedup_key`（`user_id|published_at`）去重入库；清理历史冗余用 `bash backend/scripts/dedup_notes.sh [--apply]`（默认 dry-run）。`/alerts` 三类告警：负面单条 / 关键词负面率 / 声量突增，按 `alert_id` 去重，命中即 WebSocket 推送 `alert`。

> 相关性双重过滤：入库前按"标题/正文/标签含关键词"字面过滤（`SEARCH_REQUIRE_KEYWORD_MATCH`）；入库后情感分析 LLM 顺带判语义相关性写 `relevance`（on_topic/off_topic，同名异物如"犀牛"=动物记 off_topic），所有读侧统一用 `src/db/filters.py::ON_TOPIC` 排除。**裸监控词有歧义时**（简称/缩写，如"学通"会误收"师学通"）在 `SENTIMENT_KEYWORD_HINTS` 里补该词真实指代，LLM 判相关性时带上，精度大增。**过短的缩写救不回来**：`yxt` 同时是歌手姚晓棠粉丝缩写、游戏代肝黑话、骑行俱乐部、墨水屏品牌，121 篇里几乎无一相关，否定式 hint（"非其他 yxt"）对 LLM 无效——已删词清数据。清理脚本：`purge_offtopic.sh`（字面噪声）、`purge_orphan_keywords.sh`（search_keyword 已不在监控词里的孤儿数据，`--keyword` 可定向只清某词，防呆拒绝清仍在监控的词），均 dry-run 默认、`--apply` 执行。`.env` 的三组词只在 `monitor_keywords` 空表时播种，改运行时词表后记得同步 `.env`，否则清库重启会让废词复活。改词表/hints 后重判存量：`mongosh` 清相关笔记 `relevance` 字段即可，下轮 `analyze_sentiment` 自动补判。

> `/sentiment/negative` 负面舆情工作台：后端支持负面笔记+负面评论统一条目（评论 `$lookup` 父笔记取监控词/分类），按影响力（笔记=粉丝数、评论=点赞）或时间排序，处置状态写原文档 `handle_status`（open/handled）。**评论采集关停后前端 `/dashboard/negative` 只展示笔记**（`kind=note` 写死），评论接口保留但前端不再调用；情感分布图、笔记列表的评论展开也一并移除，保持"纯笔记级舆情"口径。

> `/competitors/compare` 竞品对比：本品牌（全部品牌词聚合成一根柱，置首）+ 各竞品同场比，情绪统计全部相关笔记。竞品词组来自运行时 `monitor_keywords`（非 `.env`）。（注：曾试过按作者昵称含品牌词剔除"自家号"只算第三方，但新机构大量养 KOC 素人号、昵称无品牌名，按昵称过滤挡不住反而给假准确感，已回退。）

`/config/keywords` GET/POST/DELETE — 监控关键词运行时增删；关键词存 `monitor_keywords`，首次从 `.env` 三组词播种，采集器 `collect_keywords` 读它（不再读 `.env`）。前端按 tab（品牌/竞品/行业）分组展示、就地增删。

`init_mongodb()` 启动时为 `notes`、`comments`、`alerts`、`kol_profiles`、`monitor_keywords` 建索引。

### WebSocket 消息类型

`new_note` | `sentiment_update` | `alert` | `heartbeat`

## 关键约束

- **TikHub 每次成功调用都扣费**。采集每天只跑一次（北京 8 点 cron）；`daily_collect` 结束写 `job_state.last_run_at`，启动补采据此判"今天是否已采过"，重启/reload 当天不重复采集。
- **TikHub 一页固定 20 条**，`MAX_NOTES_PER_PAGE` 别调超过 20。
- **TikHub 已下线 `app` / `web` / `web_v2` 全系接口**（2026-07 实测均返回 404），现存只有 `app_v2` / `pgy` / `web_v3`。本项目三个端点一律走 `app_v2`：`search_notes`、`get_user_info`、`get_note_comments`。上游再改接口时，用 `curl https://api.tikhub.dev/openapi.json` 免费拉全量路径清单核对。
- **搜索接口偶发 400**，`TikHubClient.search_notes` 重试 3 次；持续失败当作"笔记被删/受限"处理。
- **搜索不保证严格按时间返回**：`sort_type=time_descending` 只是软提示，接口偶尔混排老的高互动帖（同一词前后两次结果可能不同）。故入库时用 `SEARCH_MAX_AGE_DAYS`（默认 180）兜底，丢弃超龄老帖。想抓更早的历史需下调此值或临时置 0。
- **端点写死在 `collectors/tikhub.py` 顶部常量**（`_SEARCH_PATH` / `_USER_INFO_PATH` / `_COMMENTS_PATH`），没有 provider 优先级配置。

## 环境配置

复制 `backend/.env.example` 为 `backend/.env`，必填：

| 变量 | 说明 |
|------|------|
| `TIKHUB_TOKEN` | TikHub API token（参考 https://tikhub.io） |
| `MONGODB_URL` | MongoDB 连接串，默认 `localhost:27017` |
| `MONITOR_KEYWORDS` | JSON 数组，如 `["口红","猫粮"]` |
| `COMPETITORS` | JSON 数组 |

## 技术栈

- 后端：Python 3.11+、FastAPI、MongoDB（motor 异步驱动）、APScheduler、Pydantic v2
- 情感分析：LLM（OpenAI 兼容接口，现用 DeepSeek，`SENTIMENT_PROVIDER=llm`），同一调用顺带判笔记与监控词的语义相关性；LLM 失败降级规则匹配（`analyzers/sentiment_service.py`）
- 前端：Next.js 16、React 19、Tailwind CSS 4、TypeScript（`frontend/`）
- 包管理：后端用 uv（禁止 pip/poetry）；前端用 npm

## 前端

```bash
# 开发启动（端口 3000）
cd frontend && bash scripts/dev.sh

# 生产构建
cd frontend && npm run build
```

## 根目录脚本

- `scripts/dev-all.sh`：同时启动前后端，阻塞运行，`Ctrl-C` 一起关闭
- `scripts/smoke.sh`：检查 dashboard 与后端 API 连通

### 前端结构

```
frontend/src/
  app/
    dashboard/page.tsx          — 小红书舆情主页（WebSocketProvider 包裹）
    dashboard/kol/page.tsx      — KOL 挖掘页
    dashboard/negative/page.tsx — 负面舆情工作台
  components/
    xhs-sentiment/       — header, category-tabs, keyword-manager, notes-table,
                           hot-topics, realtime-feed, alert-panel, xhs-sentiment-dashboard
    negative/            — negative-workspace（负面处置流）
    kol/                 — kol-discovery（页壳+筛选）, kol-row（行/分类校正/展开）, kol-notes（相关笔记）
    charts/              — sentiment-donut, trend-line, competitor-bar（Recharts）
    ui/                  — card, badge, skeleton
  lib/
    api/                 — 按域拆：client(BASE/get/post) + xhs + alerts + kol + negative，index 汇出
    websocket.tsx        — WebSocketProvider（单连接）+ useWebSocket 订阅 hook
    utils.ts             — 日期/数字格式化，noteUrl 原文链接，SENTIMENT_CONFIG
  types/                 — 按域拆：note / alert / kol / negative / ws，index 汇出
```

前端环境变量在 `frontend/.env.local`：`NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`。
