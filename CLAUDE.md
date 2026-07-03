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

**采集链路**：TikHub API（`api.tikhub.dev`）→ `TikHubClient` → `DataCollector` → MongoDB → Senta 情感分析 → WebSocket 推送

> 官方情报（UCAS/大学官网/考试局/签证）已拆分为独立项目 `study-abroad-intel`，本仓库只做小红书舆情。

### 模块关系

```
APScheduler (collectors/scheduler.py)
  ├─ collect_keywords   每 30 分钟：关键词 → 入库新笔记 → 广播
  ├─ collect_comments   每 30 分钟：6h 未刷新的笔记拉评论
  ├─ analyze_sentiment  每 15 分钟：补齐缺失的 sentiment 字段；判负即触发告警
  └─ scan_alerts        每 30 分钟：按关键词扫负面率/声量突增 → alerts
         │
         ▼
  DataCollector (collectors/xhs_api.py) — 采集 + upsert
         │
         ▼
  TikHubClient (collectors/tikhub.py)
         │  _ProviderChain：按 TIKHUB_PROVIDER_PRIORITY 顺序尝试
         │  上游 400/网关错自动 fallback 下一个 provider
         ▼
  AppV2Adapter  ──┐   目前 token 套餐不含 /app_v2/，会被跳过
  AppAdapter    ──┘   retry_on_400=1 缓解"冷启动首次 400"
         │
         ▼
  https://api.tikhub.dev/api/v1/xiaohongshu/{app_v2|app}/...
```

### API 路由（挂在 `/api/` 前缀下）

`/notes` `/comments` `/sentiment` `/trends` `/competitors` `/alerts` `/kol` — 全部读 MongoDB。

> `/kol` KOL 挖掘：聚合 `notes` 作者 → 相关度/互动/情感打分 → 候选池；昵称含 `渊学通`/`英通` 判自家并排除，命中词全属竞品词的打竞品标。人工态（shortlist/reject）与付费富化（`get_user_info` 补粉丝数，有每日上限+缓存）存 `kol_profiles`。设计见 `docs/kol-discovery-design.md`。

> 数据模型要点：笔记 `category` 只存桶值（brand/competitor/industry），真正的关键词在 `search_keyword`。竞品/趋势/告警一律按 `search_keyword` 聚合、用 `published_at`（发布时间）做时间轴，而非 `collected_at`（抓取时间）。同一篇笔记上游会返回变体 `note_id`，故按 `dedup_key`（`user_id|published_at`）去重入库；清理历史冗余用 `bash backend/scripts/dedup_notes.sh [--apply]`（默认 dry-run）。`/alerts` 三类告警：负面单条 / 关键词负面率 / 声量突增，按 `alert_id` 去重，命中即 WebSocket 推送 `alert`。

`/config/keywords` GET/POST/DELETE — 监控关键词运行时增删；关键词存 `monitor_keywords`，首次从 `.env` 三组词播种，采集器 `collect_keywords` 读它（不再读 `.env`）。前端按 tab（品牌/竞品/行业）分组展示、就地增删。

`init_mongodb()` 启动时为 `notes`、`comments`、`alerts`、`kol_profiles`、`monitor_keywords` 建索引。

### WebSocket 消息类型

`new_note` | `sentiment_update` | `alert` | `heartbeat`

## 关键约束

- **TikHub 每次成功调用都扣费**。开发期避免频繁重启触发 `collect_keywords` 立即跑（`scheduler.py` 里配了 `next_run_time=+10s`）。
- **TikHub 一页固定 20 条**，`MAX_NOTES_PER_PAGE` 别调超过 20。
- **app 接口偶发 400**，adapter 内部会重试 1 次；持续失败当作"笔记被删/受限"处理。
- **provider 优先级**：开通 app_v2 后把 `.env` 的 `TIKHUB_PROVIDER_PRIORITY` 改成 `["app_v2","app"]` 即可自动切换。

## 环境配置

复制 `backend/.env.example` 为 `backend/.env`，必填：

| 变量 | 说明 |
|------|------|
| `TIKHUB_TOKEN` | TikHub API token（参考 https://tikhub.io） |
| `MONGODB_URL` | MongoDB 连接串，默认 `localhost:27017` |
| `MONITOR_KEYWORDS` | JSON 数组，如 `["口红","猫粮"]` |
| `COMPETITORS` | JSON 数组 |
| `TIKHUB_PROVIDER_PRIORITY` | 默认 `["app"]`；开通 app_v2 后改 `["app_v2","app"]` |

## 技术栈

- 后端：Python 3.11+、FastAPI、MongoDB（motor 异步驱动）、APScheduler、Pydantic v2
- 情感分析：百度 Senta（ERNIE）；未安装时自动降级规则匹配
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
  components/
    xhs-sentiment/       — header, category-tabs, keyword-manager, notes-table,
                           hot-topics, realtime-feed, alert-panel, xhs-sentiment-dashboard
    kol/                 — kol-discovery
    charts/              — sentiment-donut, trend-line, competitor-bar（Recharts）
    ui/                  — card, badge, skeleton
  lib/
    api/                 — 按域拆：client(BASE/get/post) + xhs + alerts + kol，index 汇出
    websocket.tsx        — WebSocketProvider（单连接）+ useWebSocket 订阅 hook
    utils.ts             — 日期/数字格式化，SENTIMENT_CONFIG
  types/                 — 按域拆：note / alert / kol / ws，index 汇出
```

前端环境变量在 `frontend/.env.local`：`NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`。
