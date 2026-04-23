# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

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

**数据流**：TikHub API（`api.tikhub.dev`）→ `TikHubClient` → `DataCollector` → MongoDB → Senta 情感分析 → WebSocket 推送

### 模块关系

```
APScheduler (collectors/scheduler.py)
  ├─ collect_keywords   每 30 分钟：关键词 → 入库新笔记 → 广播
  ├─ collect_comments   每 30 分钟：6h 未刷新的笔记拉评论
  └─ analyze_sentiment  每 15 分钟：补齐缺失的 sentiment 字段
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

`/notes` `/comments` `/sentiment` `/trends` `/competitors` — 全部读 MongoDB，`init_mongodb()` 启动时建索引。

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
cd frontend && npm run dev

# 生产构建
cd frontend && npm run build
```

### 前端结构

```
frontend/src/
  app/
    dashboard/page.tsx   — 主 Dashboard（Client Component）
  components/
    dashboard/           — header, stats-overview, notes-table, hot-topics, realtime-feed
    charts/              — sentiment-donut, trend-line, competitor-bar（Recharts）
    ui/                  — card, badge, skeleton
  lib/
    api.ts               — fetch 封装，读 NEXT_PUBLIC_API_URL
    websocket.ts         — useWebSocket hook，读 NEXT_PUBLIC_WS_URL，自动重连
    utils.ts             — 日期/数字格式化，SENTIMENT_CONFIG
  types/index.ts         — 与后端模型对齐的 TS 类型
```

前端环境变量在 `frontend/.env.local`：`NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL`。
