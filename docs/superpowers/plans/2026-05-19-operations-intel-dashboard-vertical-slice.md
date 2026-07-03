# Operations Intel Dashboard Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一个可运行的“运营工作台”纵向切片：`/dashboard` 变成新的按来源情报面板，使用真实小红书数据和 fixture/seed 驱动的 `UCAS / 海外大学官网 / 媒体公众号` 数据；老的小红书舆情视图继续保留在独立路由。

**Architecture:** 先做 contract-first 的纵向切片，不同时启动所有真实抓取器。后端新增统一的 `intel_items` 领域模型、Mongo collection 和读取 API，用适配器把现有小红书 `notes` 归一化进新视图，并用 seed 数据补齐其余来源，先验证信息架构、摘要密度和导航逻辑。前端新增 operations dashboard 组件树，把当前 `/dashboard` 迁到 legacy 路由，降低回归风险。

**Tech Stack:** FastAPI, Motor/MongoDB, Pydantic v2, Next.js 16, React 19, TypeScript, ESLint

---

## 为什么先这样拆

这份 spec 同时覆盖了 3 个相对独立的子系统：

1. 统一情报数据契约
2. 新来源接入
3. 前端信息架构重做

如果一次性并行推进，最容易卡在“抓取还没好，UI 无法验证；UI 在变，后端 contract 也在变”。因此第一阶段只做 `纵向切片`：

- 小红书走真实数据
- 其他来源先走 seed / fixture
- 目标是尽快把 `/dashboard` 的新结构跑起来

这阶段验收通过后，再开第二份计划做真实 `UCAS / 大学官网 / 公众号` 抓取器。

---

## 文件变更地图

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/src/models/intel.py` | Create | 统一情报模型与来源枚举 |
| `backend/src/services/intel_feed.py` | Create | 统一情报读取、总览聚合、来源页查询 |
| `backend/src/services/intel_seed.py` | Create | 读取 fixture 并 upsert 到 `intel_items` |
| `backend/src/api/intel.py` | Create | 新 Dashboard 所需 API |
| `backend/src/api/config.py` | Modify | 增加来源导航元信息接口 |
| `backend/src/db/mongodb.py` | Modify | 为 `intel_items` 建索引 |
| `backend/main.py` | Modify | 注册 `/api/intel` 路由 |
| `backend/scripts/test.sh` | Create | 后端 pytest wrapper，统一测试入口 |
| `backend/tests/conftest.py` | Create | 测试 app / Mongo stub 基础设施 |
| `backend/tests/services/test_intel_feed.py` | Create | 服务层测试 |
| `backend/tests/api/test_intel_api.py` | Create | API 测试 |
| `backend/temp/intel_seed.json` | Create | 开发期 seed 数据 |
| `backend/scripts/seed_intel_demo.sh` | Create | 通过脚本装填演示数据 |
| `frontend/src/components/dashboard/legacy-xhs-dashboard.tsx` | Create | 保存旧 dashboard 布局 |
| `frontend/src/app/dashboard/legacy/page.tsx` | Create | 旧 dashboard 新路由 |
| `frontend/src/app/dashboard/page.tsx` | Modify | 改成 operations dashboard 入口 |
| `frontend/src/types/intel.ts` | Create | 新面板专用 TS 类型 |
| `frontend/src/types/index.ts` | Modify | 统一导出新类型 |
| `frontend/src/lib/intel-api.ts` | Create | 新 API fetch 封装 |
| `frontend/src/components/operations-dashboard/sidebar.tsx` | Create | 左侧来源导航 |
| `frontend/src/components/operations-dashboard/helper-rail.tsx` | Create | 右侧轻辅助栏 |
| `frontend/src/components/operations-dashboard/intel-card.tsx` | Create | 总览/来源页通用卡片 |
| `frontend/src/components/operations-dashboard/overview-panel.tsx` | Create | 总览页 |
| `frontend/src/components/operations-dashboard/source-panel.tsx` | Create | 来源详情页公共骨架 |
| `frontend/src/components/operations-dashboard/source-header.tsx` | Create | 来源页头部 |
| `frontend/src/components/operations-dashboard/source-list.tsx` | Create | 来源页卡片列表 |
| `frontend/src/components/operations-dashboard/empty-state.tsx` | Create | 空状态 |
| `frontend/src/components/operations-dashboard/error-state.tsx` | Create | 异常状态 |
| `frontend/src/components/operations-dashboard/loading-state.tsx` | Create | 加载态 |
| `frontend/src/components/operations-dashboard/source-sections/xiaohongshu-section.tsx` | Create | 小红书来源模块 |
| `frontend/src/components/operations-dashboard/source-sections/ucas-section.tsx` | Create | UCAS 来源模块 |
| `frontend/src/components/operations-dashboard/source-sections/university-section.tsx` | Create | 大学官网来源模块 |
| `frontend/src/components/operations-dashboard/source-sections/wechat-section.tsx` | Create | 媒体公众号来源模块 |
| `frontend/scripts/dev.sh` | Create | 前端 dev wrapper，符合 scripts 约束 |
| `frontend/scripts/lint.sh` | Create | 前端 lint wrapper |
| `docs/superpowers/plans/2026-05-19-operations-intel-dashboard-real-sources.md` | Later | 第二阶段真实抓取器计划，不在本任务实现 |

---

## Task 1: 把旧 Dashboard 保住，并补前端脚本入口

**Files:**
- Create: `frontend/scripts/dev.sh`
- Create: `frontend/scripts/lint.sh`
- Create: `frontend/src/components/dashboard/legacy-xhs-dashboard.tsx`
- Create: `frontend/src/app/dashboard/legacy/page.tsx`
- Modify: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: 创建前端脚本 wrapper**

在 `frontend/scripts/dev.sh` 写入：

```bash
#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

npm run dev
```

在 `frontend/scripts/lint.sh` 写入：

```bash
#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

npm run lint
```

然后执行：

```bash
chmod +x /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend/scripts/dev.sh
chmod +x /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend/scripts/lint.sh
```

- [ ] **Step 2: 提取现有 dashboard 为 legacy 组件**

把当前 `frontend/src/app/dashboard/page.tsx` 的主体 JSX 和 state 逻辑整体搬到新文件 `frontend/src/components/dashboard/legacy-xhs-dashboard.tsx`，导出：

```tsx
export function LegacyXhsDashboard() {
  return <div className="min-h-screen bg-[#09090b]">{/* existing content */}</div>;
}
```

`frontend/src/app/dashboard/legacy/page.tsx` 写成：

```tsx
import { LegacyXhsDashboard } from "@/components/dashboard/legacy-xhs-dashboard";

export default function LegacyDashboardPage() {
  return <LegacyXhsDashboard />;
}
```

- [ ] **Step 3: 先让 `/dashboard` 暂时重定向到 legacy，确保迁移过程不炸**

在 `frontend/src/app/dashboard/page.tsx` 先写最小安全壳：

```tsx
import { redirect } from "next/navigation";

export default function DashboardPage() {
  redirect("/dashboard/legacy");
}
```

运行：

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend && bash scripts/dev.sh
```

预期：

- `http://localhost:3000/dashboard` 跳到 `/dashboard/legacy`
- 老页面正常显示

- [ ] **Step 4: 提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add frontend/scripts/dev.sh frontend/scripts/lint.sh frontend/src/components/dashboard/legacy-xhs-dashboard.tsx frontend/src/app/dashboard/legacy/page.tsx frontend/src/app/dashboard/page.tsx
git commit -m "refactor: preserve legacy xhs dashboard before operations rewrite"
```

---

## Task 2: 建立统一情报模型与服务层

**Files:**
- Create: `backend/scripts/test.sh`
- Create: `backend/src/models/intel.py`
- Create: `backend/src/services/intel_feed.py`
- Modify: `backend/src/db/mongodb.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/services/test_intel_feed.py`

- [ ] **Step 1: 先补后端测试脚本入口**

`backend/scripts/test.sh` 写入：

```bash
#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

pytest "$@"
```

然后执行：

```bash
chmod +x /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend/scripts/test.sh
```

- [ ] **Step 2: 先写服务层失败测试**

`backend/tests/services/test_intel_feed.py` 先写三组测试：

```python
from datetime import datetime, timezone

from src.models.intel import IntelItem, IntelSourceType
from src.services.intel_feed import build_overview_sections, build_helper_rail


def make_item(source_type: IntelSourceType, source_name: str, title: str) -> IntelItem:
    return IntelItem(
        item_id=f"{source_type.value}-{title}",
        source_type=source_type,
        source_name=source_name,
        title=title,
        summary_short=f"{title} short",
        summary_long=f"{title} long",
        impact_targets=["本科"],
        published_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 5, 19, 8, 30, tzinfo=timezone.utc),
        original_url=f"https://example.com/{title}",
    )


def test_build_overview_sections_groups_by_source_type():
    items = [
        make_item(IntelSourceType.XIAOHONGSHU, "小红书", "xhs-1"),
        make_item(IntelSourceType.UCAS, "UCAS", "ucas-1"),
    ]
    sections = build_overview_sections(items)
    assert [section.source_key for section in sections] == ["xiaohongshu", "ucas"]


def test_build_overview_sections_limits_preview_count():
    items = [make_item(IntelSourceType.UCAS, "UCAS", f"ucas-{idx}") for idx in range(5)]
    sections = build_overview_sections(items)
    assert len(sections[0].preview_items) == 3


def test_build_helper_rail_counts_impact_targets():
    items = [
        make_item(IntelSourceType.UCAS, "UCAS", "ucas-1"),
        make_item(IntelSourceType.UCAS, "UCAS", "ucas-2").model_copy(
            update={"impact_targets": ["硕士", "申请季"]}
        ),
    ]
    rail = build_helper_rail(items)
    assert rail.top_counts["本科"] == 1
    assert rail.top_counts["硕士"] == 1
```

运行：

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/services/test_intel_feed.py -v
```

预期：失败，提示 `src.models.intel` 或 `src.services.intel_feed` 不存在。

- [ ] **Step 3: 实现统一模型**

`backend/src/models/intel.py` 写入最小模型：

```python
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class IntelSourceType(str, Enum):
    XIAOHONGSHU = "xiaohongshu"
    UCAS = "ucas"
    UNIVERSITY_SITE = "university_site"
    WECHAT_MEDIA = "wechat_media"


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


class IntelOverviewSection(BaseModel):
    source_key: str
    source_label: str
    total_items: int
    preview_items: list[IntelItem]


class IntelHelperRail(BaseModel):
    highlight_count: int
    top_counts: dict[str, int]
```

- [ ] **Step 4: 实现服务层纯函数和 Mongo 读取入口**

`backend/src/services/intel_feed.py` 先实现纯函数，再留 repository 入口：

```python
from collections import Counter
from collections.abc import Iterable

from src.models.intel import IntelHelperRail, IntelItem, IntelOverviewSection, IntelSourceType


SOURCE_LABELS = {
    IntelSourceType.XIAOHONGSHU: "小红书",
    IntelSourceType.UCAS: "UCAS",
    IntelSourceType.UNIVERSITY_SITE: "海外大学官网",
    IntelSourceType.WECHAT_MEDIA: "媒体公众号",
}


def build_overview_sections(items: Iterable[IntelItem]) -> list[IntelOverviewSection]:
    grouped: dict[IntelSourceType, list[IntelItem]] = {}
    for item in items:
        grouped.setdefault(item.source_type, []).append(item)

    sections: list[IntelOverviewSection] = []
    for source_type in SOURCE_LABELS:
        source_items = grouped.get(source_type, [])
        sections.append(
            IntelOverviewSection(
                source_key=source_type.value,
                source_label=SOURCE_LABELS[source_type],
                total_items=len(source_items),
                preview_items=source_items[:3],
            )
        )
    return sections


def build_helper_rail(items: Iterable[IntelItem]) -> IntelHelperRail:
    counter = Counter()
    item_list = list(items)
    for item in item_list:
        counter.update(item.impact_targets)
    return IntelHelperRail(highlight_count=min(3, len(item_list)), top_counts=dict(counter.most_common(5)))
```

`backend/src/db/mongodb.py` 加索引：

```python
intel_items = self.db["intel_items"]
await intel_items.create_index("item_id", unique=True)
await intel_items.create_index([("source_type", 1), ("published_at", -1)])
await intel_items.create_index([("source_type", 1), ("source_group", 1), ("published_at", -1)])
await intel_items.create_index([("school_name", 1), ("published_at", -1)])
```

- [ ] **Step 5: 跑测试**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/services/test_intel_feed.py -v
```

预期：3 个测试通过。

- [ ] **Step 6: 提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add backend/scripts/test.sh backend/src/models/intel.py backend/src/services/intel_feed.py backend/src/db/mongodb.py backend/tests/conftest.py backend/tests/services/test_intel_feed.py
git commit -m "feat: add unified intel domain model and feed helpers"
```

---

## Task 3: 提供 seed 数据与 `/api/intel` API

**Files:**
- Create: `backend/src/services/intel_seed.py`
- Create: `backend/src/api/intel.py`
- Modify: `backend/src/api/config.py`
- Modify: `backend/main.py`
- Create: `backend/temp/intel_seed.json`
- Create: `backend/scripts/seed_intel_demo.sh`
- Create: `backend/tests/api/test_intel_api.py`

- [ ] **Step 1: 写 API 失败测试**

`backend/tests/api/test_intel_api.py` 先写：

```python
from fastapi.testclient import TestClient

from main import app


def test_get_source_navigation_metadata():
    client = TestClient(app)
    response = client.get("/api/config/source-nav")
    assert response.status_code == 200
    assert response.json()["items"][0]["key"] == "overview"


def test_get_intel_overview_shape():
    client = TestClient(app)
    response = client.get("/api/intel/overview")
    assert response.status_code == 200
    payload = response.json()
    assert "sections" in payload
    assert "helper_rail" in payload


def test_get_intel_source_feed_accepts_source_key():
    client = TestClient(app)
    response = client.get("/api/intel/sources/ucas")
    assert response.status_code == 200
    assert "items" in response.json()
```

运行：

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/api/test_intel_api.py -v
```

预期：失败，提示路由不存在。

- [ ] **Step 2: 准备 seed fixture**

`backend/temp/intel_seed.json` 放 8-12 条最小演示数据，至少覆盖：

- `UCAS` 2 条
- `海外大学官网` 4 条，其中 2 条属于重点学校
- `媒体公众号` 2 条

单条 JSON 结构示例：

```json
{
  "item_id": "ucas-2026-cycle-update",
  "source_type": "ucas",
  "source_name": "UCAS",
  "title": "2026 cycle key dates updated",
  "summary_short": "UCAS 更新了 2026 申请周期关键节点。",
  "summary_long": "UCAS 调整了 2026 申请时间线，申请开启和部分节点提醒有所变化。对申请季内容节奏和提醒类文章选题有直接影响。",
  "impact_targets": ["本科", "申请季"],
  "published_at": "2026-05-19T08:00:00Z",
  "collected_at": "2026-05-19T08:10:00Z",
  "original_url": "https://www.ucas.com/example"
}
```

- [ ] **Step 3: 实现 seed 服务和脚本**

`backend/src/services/intel_seed.py` 提供：

```python
import json
from pathlib import Path

from src.db.mongodb import mongodb


async def seed_intel_items(seed_path: Path) -> int:
    payload = json.loads(seed_path.read_text())
    collection = mongodb.get_collection("intel_items")
    count = 0
    for item in payload:
        await collection.update_one({"item_id": item["item_id"]}, {"$set": item}, upsert=True)
        count += 1
    return count
```

`backend/scripts/seed_intel_demo.sh` 写成：

```bash
#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python - <<'PY'
import asyncio
from pathlib import Path

from src.db.mongodb import close_mongodb, init_mongodb
from src.services.intel_seed import seed_intel_items


async def main():
    await init_mongodb()
    count = await seed_intel_items(Path("temp/intel_seed.json"))
    print(f"seeded={count}")
    await close_mongodb()


asyncio.run(main())
PY
```

- [ ] **Step 4: 实现路由**

`backend/src/api/config.py` 增加：

```python
@router.get("/source-nav")
async def get_source_nav():
    return {
        "items": [
            {"key": "overview", "label": "总览"},
            {"key": "xiaohongshu", "label": "小红书"},
            {"key": "ucas", "label": "UCAS"},
            {"key": "university_site", "label": "海外大学官网"},
            {"key": "wechat_media", "label": "媒体公众号"},
        ]
    }
```

`backend/src/api/intel.py` 暂时暴露：

```python
@router.get("/overview")
async def get_intel_overview():
    ...


@router.get("/sources/{source_key}")
async def get_source_feed(source_key: str):
    ...
```

返回 shape 固定为：

```python
{
    "sections": [...],
    "helper_rail": {...},
}
```

和：

```python
{
    "source_key": source_key,
    "items": [...],
    "helper_rail": {...},
}
```

`backend/main.py` 注册：

```python
from src.api import intel
app.include_router(intel.router, prefix="/api/intel", tags=["运营情报"])
```

- [ ] **Step 5: 跑 API 测试和 seed smoke**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/seed_intel_demo.sh
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/api/test_intel_api.py -v
```

预期：

- 脚本输出 `seeded=...`
- API 测试通过

- [ ] **Step 6: 提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add backend/src/services/intel_seed.py backend/src/api/intel.py backend/src/api/config.py backend/main.py backend/temp/intel_seed.json backend/scripts/seed_intel_demo.sh backend/tests/api/test_intel_api.py
git commit -m "feat: add fixture-backed intel overview api"
```

---

## Task 4: 把现有小红书数据接进统一情报流

**Files:**
- Modify: `backend/src/services/intel_feed.py`
- Modify: `backend/src/models/intel.py`
- Modify: `backend/tests/services/test_intel_feed.py`

- [ ] **Step 1: 先补 xiaohongshu 适配测试**

在 `backend/tests/services/test_intel_feed.py` 增加：

```python
from datetime import datetime, timezone

from src.models.note import AuthorInfo, Note, NoteType, StatsInfo
from src.services.intel_feed import note_to_intel_item


def test_note_to_intel_item_maps_note_fields():
    note = Note(
        note_id="xhs-1",
        title="英国本科申请经验",
        content="分享申请过程中的时间节点和材料准备。",
        type=NoteType.NORMAL,
        author=AuthorInfo(user_id="u1", nickname="作者", fans_count=1),
        stats=StatsInfo(),
        published_at=datetime(2026, 5, 19, 8, 0, tzinfo=timezone.utc),
        collected_at=datetime(2026, 5, 19, 8, 30, tzinfo=timezone.utc),
        keywords=["英国本科"],
        category="brand",
    )

    item = note_to_intel_item(note)

    assert item.source_type.value == "xiaohongshu"
    assert item.source_name == "小红书"
    assert item.title == note.title
    assert item.summary_short
```

运行：

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/services/test_intel_feed.py -v
```

预期：失败，提示 `note_to_intel_item` 不存在。

- [ ] **Step 2: 实现 note adapter**

在 `backend/src/services/intel_feed.py` 增加：

```python
from src.models.note import Note


def note_to_intel_item(note: Note) -> IntelItem:
    short = note.title if note.content.strip() == "" else note.content.strip()[:80]
    long_summary = note.content.strip()[:180] or note.title
    impact_targets = []
    if "本科" in note.title or "本科" in note.content:
        impact_targets.append("本科")
    if "硕士" in note.title or "硕士" in note.content:
        impact_targets.append("硕士")
    return IntelItem(
        item_id=f"xhs-{note.note_id}",
        source_type=IntelSourceType.XIAOHONGSHU,
        source_name="小红书",
        title=note.title,
        summary_short=short,
        summary_long=long_summary,
        impact_targets=impact_targets,
        published_at=note.published_at,
        collected_at=note.collected_at,
        original_url=f"https://www.xiaohongshu.com/explore/{note.note_id}",
    )
```

- [ ] **Step 3: 在 overview/source feed 中合并两类数据**

`backend/src/services/intel_feed.py` 新增读取策略：

```python
async def list_intel_items_for_source(source_key: str, limit: int = 20) -> list[IntelItem]:
    if source_key == "xiaohongshu":
        notes = await mongodb.get_collection("notes").find({}).sort("collected_at", -1).limit(limit).to_list(length=limit)
        return [note_to_intel_item(Note(**note)) for note in notes]

    rows = await mongodb.get_collection("intel_items").find({"source_type": source_key}).sort("published_at", -1).limit(limit).to_list(length=limit)
    return [IntelItem(**row) for row in rows]
```

总览 API 则把：

- 小红书：实时从 `notes` 归一化
- 其余来源：从 `intel_items` 读取

这样可以做到首版 UI 已经是真实 xhs + fixture 其他来源。

- [ ] **Step 4: 跑回归测试**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/services/test_intel_feed.py tests/api/test_intel_api.py -v
```

预期：全部通过。

- [ ] **Step 5: 提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add backend/src/services/intel_feed.py backend/src/models/intel.py backend/tests/services/test_intel_feed.py
git commit -m "feat: merge xiaohongshu notes into unified intel feed"
```

---

## Task 5: 前端建立新数据契约和 fetch 层

**Files:**
- Create: `frontend/src/types/intel.ts`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/lib/intel-api.ts`

- [ ] **Step 1: 新建 TS 类型**

`frontend/src/types/intel.ts` 写入：

```ts
export type IntelSourceKey =
  | "overview"
  | "xiaohongshu"
  | "ucas"
  | "university_site"
  | "wechat_media";

export interface IntelItem {
  item_id: string;
  source_type: Exclude<IntelSourceKey, "overview">;
  source_name: string;
  title: string;
  summary_short: string;
  summary_long: string;
  impact_targets: string[];
  published_at: string;
  collected_at: string;
  original_url: string;
  school_name?: string;
  source_group?: string;
}

export interface IntelOverviewSection {
  source_key: Exclude<IntelSourceKey, "overview">;
  source_label: string;
  total_items: number;
  preview_items: IntelItem[];
}

export interface IntelHelperRail {
  highlight_count: number;
  top_counts: Record<string, number>;
}

export interface IntelOverviewResponse {
  sections: IntelOverviewSection[];
  helper_rail: IntelHelperRail;
}

export interface IntelSourceResponse {
  source_key: Exclude<IntelSourceKey, "overview">;
  items: IntelItem[];
  helper_rail: IntelHelperRail;
}

export interface SourceNavItem {
  key: IntelSourceKey;
  label: string;
}
```

- [ ] **Step 2: 统一导出**

在 `frontend/src/types/index.ts` 末尾加：

```ts
export * from "./intel";
```

- [ ] **Step 3: 新建 fetch 层**

`frontend/src/lib/intel-api.ts` 写：

```ts
import type { IntelOverviewResponse, IntelSourceKey, IntelSourceResponse, SourceNavItem } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export function fetchSourceNav(): Promise<{ items: SourceNavItem[] }> {
  return get("/api/config/source-nav");
}

export function fetchIntelOverview(): Promise<IntelOverviewResponse> {
  return get("/api/intel/overview");
}

export function fetchIntelSource(sourceKey: Exclude<IntelSourceKey, "overview">): Promise<IntelSourceResponse> {
  return get(`/api/intel/sources/${sourceKey}`);
}
```

- [ ] **Step 4: lint**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend && bash scripts/lint.sh
```

预期：通过；若报路径别名或重复导出错误，先修掉后再继续。

- [ ] **Step 5: 提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add frontend/src/types/intel.ts frontend/src/types/index.ts frontend/src/lib/intel-api.ts
git commit -m "feat: add operations dashboard frontend contract"
```

---

## Task 6: 建立 operations dashboard 骨架组件

**Files:**
- Create: `frontend/src/components/operations-dashboard/sidebar.tsx`
- Create: `frontend/src/components/operations-dashboard/helper-rail.tsx`
- Create: `frontend/src/components/operations-dashboard/intel-card.tsx`
- Create: `frontend/src/components/operations-dashboard/overview-panel.tsx`
- Create: `frontend/src/components/operations-dashboard/source-header.tsx`
- Create: `frontend/src/components/operations-dashboard/source-list.tsx`
- Create: `frontend/src/components/operations-dashboard/source-panel.tsx`
- Create: `frontend/src/components/operations-dashboard/loading-state.tsx`
- Create: `frontend/src/components/operations-dashboard/empty-state.tsx`
- Create: `frontend/src/components/operations-dashboard/error-state.tsx`

- [ ] **Step 1: 先做可渲染的静态骨架**

先把 `sidebar.tsx` 写成最小版：

```tsx
import type { IntelSourceKey, SourceNavItem } from "@/types";

interface SidebarProps {
  items: SourceNavItem[];
  activeKey: IntelSourceKey;
  onChange: (key: IntelSourceKey) => void;
}

export function OperationsSidebar({ items, activeKey, onChange }: SidebarProps) {
  return (
    <aside className="w-56 shrink-0 border-r border-[#27272a] p-4">
      <nav className="space-y-1">
        {items.map((item) => (
          <button
            key={item.key}
            onClick={() => onChange(item.key)}
            className={item.key === activeKey ? "w-full rounded bg-[#18181b] px-3 py-2 text-left text-white" : "w-full rounded px-3 py-2 text-left text-[#a1a1aa] hover:bg-[#111113]"}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
```

`intel-card.tsx` 先实现可复用节奏：

```tsx
import type { IntelItem } from "@/types";

interface IntelCardProps {
  item: IntelItem;
  compact?: boolean;
}

export function IntelCard({ item, compact = false }: IntelCardProps) {
  return (
    <article className="rounded-[10px] border border-[#27272a] bg-[#111113] p-4">
      <h3 className="text-sm font-medium text-white">{item.title}</h3>
      <p className="mt-2 text-sm leading-6 text-[#d4d4d8]">
        {compact ? item.summary_short : item.summary_long}
      </p>
      <div className="mt-3 flex items-center gap-2 text-xs text-[#71717a]">
        <span>{item.source_name}</span>
        {item.impact_targets.map((target) => (
          <span key={target} className="rounded bg-[#18181b] px-2 py-0.5">{target}</span>
        ))}
      </div>
      <a className="mt-3 inline-flex text-xs text-[#93c5fd] hover:text-white" href={item.original_url} target="_blank" rel="noreferrer">
        去原文
      </a>
    </article>
  );
}
```

- [ ] **Step 2: 组装 overview/source 公共面板**

`overview-panel.tsx` 只做“轻扫”：

```tsx
import type { IntelOverviewResponse } from "@/types";
import { IntelCard } from "./intel-card";

export function OverviewPanel({ data }: { data: IntelOverviewResponse }) {
  return (
    <section className="space-y-6">
      {data.sections.map((section) => (
        <div key={section.source_key} className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-white">{section.source_label}</h2>
            <span className="text-xs text-[#71717a]">今日 {section.total_items} 条</span>
          </div>
          <div className="space-y-3">
            {section.preview_items.map((item) => (
              <IntelCard key={item.item_id} item={item} compact />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
```

`source-panel.tsx` 做“深读”：

```tsx
import type { IntelSourceResponse } from "@/types";
import { IntelCard } from "./intel-card";
import { SourceHeader } from "./source-header";

export function SourcePanel({ data }: { data: IntelSourceResponse }) {
  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key} itemCount={data.items.length} />
      <div className="space-y-3">
        {data.items.map((item) => (
          <IntelCard key={item.item_id} item={item} />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: 加入 loading / empty / error 组件**

最小要求：

- `loading-state.tsx` 提供 3 张 skeleton 卡片
- `empty-state.tsx` 文案为“今日暂无新增”
- `error-state.tsx` 文案为“该来源暂时无法加载，请稍后重试”

- [ ] **Step 4: lint**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend && bash scripts/lint.sh
```

- [ ] **Step 5: 提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add frontend/src/components/operations-dashboard
git commit -m "feat: add operations dashboard shell components"
```

---

## Task 7: 用真实 API 接通 `/dashboard`

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: 改写 dashboard 页面状态机**

把 `frontend/src/app/dashboard/page.tsx` 从 legacy redirect 改成新的 client page：

```tsx
"use client";

import { useEffect, useState } from "react";

import { fetchIntelOverview, fetchIntelSource, fetchSourceNav } from "@/lib/intel-api";
import type { IntelOverviewResponse, IntelSourceKey, IntelSourceResponse, SourceNavItem } from "@/types";
import { OperationsSidebar } from "@/components/operations-dashboard/sidebar";
import { OperationsHelperRail } from "@/components/operations-dashboard/helper-rail";
import { OverviewPanel } from "@/components/operations-dashboard/overview-panel";
import { SourcePanel } from "@/components/operations-dashboard/source-panel";
import { OperationsLoadingState } from "@/components/operations-dashboard/loading-state";
import { OperationsErrorState } from "@/components/operations-dashboard/error-state";
```

状态至少包含：

```tsx
const [navItems, setNavItems] = useState<SourceNavItem[]>([]);
const [activeKey, setActiveKey] = useState<IntelSourceKey>("overview");
const [overview, setOverview] = useState<IntelOverviewResponse | null>(null);
const [sourceData, setSourceData] = useState<IntelSourceResponse | null>(null);
const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
```

- [ ] **Step 2: 按视图加载**

加载策略：

```tsx
useEffect(() => {
  fetchSourceNav().then((payload) => setNavItems(payload.items));
}, []);

useEffect(() => {
  let cancelled = false;
  setStatus("loading");

  const load = activeKey === "overview"
    ? fetchIntelOverview().then((payload) => {
        if (!cancelled) {
          setOverview(payload);
          setSourceData(null);
          setStatus("ready");
        }
      })
    : fetchIntelSource(activeKey).then((payload) => {
        if (!cancelled) {
          setSourceData(payload);
          setOverview(null);
          setStatus("ready");
        }
      });

  load.catch(() => !cancelled && setStatus("error"));
  return () => {
    cancelled = true;
  };
}, [activeKey]);
```

- [ ] **Step 3: 渲染三栏**

页面主体结构固定：

```tsx
return (
  <div className="min-h-screen bg-[#09090b] text-[#f4f4f5]">
    <main className="mx-auto flex min-h-screen max-w-screen-2xl">
      <OperationsSidebar items={navItems} activeKey={activeKey} onChange={setActiveKey} />
      <section className="min-w-0 flex-1 px-6 py-6">
        {status === "loading" && <OperationsLoadingState />}
        {status === "error" && <OperationsErrorState />}
        {status === "ready" && overview && <OverviewPanel data={overview} />}
        {status === "ready" && sourceData && <SourcePanel data={sourceData} />}
      </section>
      <OperationsHelperRail data={overview?.helper_rail ?? sourceData?.helper_rail ?? null} />
    </main>
  </div>
);
```

- [ ] **Step 4: 本地 smoke**

先 seed：

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/seed_intel_demo.sh
```

再跑前端：

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend && bash scripts/dev.sh
```

手动验收：

- `/dashboard` 默认是总览页
- 左侧有 `总览 / 小红书 / UCAS / 海外大学官网 / 媒体公众号`
- 点来源会切换主区内容
- 总览页每个来源只显示 2-3 条短摘要
- 来源页显示 2-3 句完整摘要
- `去原文` 可点开外链

- [ ] **Step 5: lint 并提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend && bash scripts/lint.sh
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add frontend/src/app/dashboard/page.tsx
git commit -m "feat: ship operations intel dashboard vertical slice"
```

---

## Task 8: 补来源特定模块和状态文案

**Files:**
- Create: `frontend/src/components/operations-dashboard/source-sections/xiaohongshu-section.tsx`
- Create: `frontend/src/components/operations-dashboard/source-sections/ucas-section.tsx`
- Create: `frontend/src/components/operations-dashboard/source-sections/university-section.tsx`
- Create: `frontend/src/components/operations-dashboard/source-sections/wechat-section.tsx`
- Modify: `frontend/src/components/operations-dashboard/source-panel.tsx`
- Modify: `frontend/src/components/operations-dashboard/helper-rail.tsx`

- [ ] **Step 1: 为不同来源加轻度差异化**

每个来源 section 只做小差异，不改核心卡片骨架：

```tsx
// xiaohongshu-section.tsx
export function XiaohongshuSection({ data }: { data: IntelSourceResponse }) {
  return <SourcePanel data={data} sectionHint="先看新增讨论，再看放量话题" />;
}

// ucas-section.tsx
export function UcasSection({ data }: { data: IntelSourceResponse }) {
  return <SourcePanel data={data} sectionHint="优先关注政策、时间节点和流程变更" />;
}
```

`university-section.tsx` 额外在 header 里标注重点学校数量。`wechat-section.tsx` 额外提示“媒体/垂类解读”。

- [ ] **Step 2: 让 helper rail 保持克制**

`helper-rail.tsx` 只渲染：

```tsx
if (!data) return null;

return (
  <aside className="hidden w-60 shrink-0 border-l border-[#27272a] px-4 py-6 xl:block">
    <div className="space-y-4">
      <div>
        <p className="text-xs text-[#71717a]">今日重点</p>
        <p className="mt-1 text-2xl font-semibold text-white">{data.highlight_count}</p>
      </div>
      <div>
        <p className="text-xs text-[#71717a]">影响对象</p>
        <div className="mt-2 space-y-2">
          {Object.entries(data.top_counts).map(([label, count]) => (
            <div key={label} className="flex items-center justify-between text-sm text-[#d4d4d8]">
              <span>{label}</span>
              <span>{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </aside>
);
```

不要加入按钮、待办、选题池入口。

- [ ] **Step 3: 手动回归**

打开：

- `http://localhost:3000/dashboard`
- `http://localhost:3000/dashboard/legacy`

确认：

- 新旧页面都能访问
- 右侧栏不抢中间主区
- 大学官网来源页能一眼区分学校名
- 小红书来源页保持“社区温度计”语气，不像官方 feed

- [ ] **Step 4: 提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add frontend/src/components/operations-dashboard
git commit -m "feat: tailor source sections for operations dashboard"
```

---

## Task 9: 文档、验证和第二阶段交接

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `frontend/README.md`
- Create: `docs/superpowers/plans/2026-05-19-operations-intel-dashboard-real-sources.md`

- [ ] **Step 1: 更新 README 和 CLAUDE 指针**

在根 `README.md` 加一段：

```md
## Operations Dashboard

The default dashboard at `/dashboard` is now the operations intel workbench.
The legacy XiaoHongShu analytics dashboard remains available at `/dashboard/legacy`.
```

在 `CLAUDE.md` 的前端结构里补充：

```md
frontend/src/components/operations-dashboard/  — 新运营情报面板组件
frontend/src/components/dashboard/legacy-xhs-dashboard.tsx — 旧舆情视图
```

在 `frontend/README.md` 替换掉默认 create-next-app 文案，至少保留：

- `bash scripts/dev.sh`
- `bash scripts/lint.sh`
- `/dashboard`
- `/dashboard/legacy`

- [ ] **Step 2: 写第二阶段计划占位文档**

创建 `docs/superpowers/plans/2026-05-19-operations-intel-dashboard-real-sources.md`，只记录下一阶段边界：

```md
# Operations Intel Dashboard Real Sources Plan

- UCAS official feed collector
- University site collector
- WeChat media collector
- Summary generation pipeline
```

不要在这一步实现第二阶段，只把 handoff 边界写清楚。

- [ ] **Step 3: 完整验证**

后端：

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend && bash scripts/test.sh tests/services/test_intel_feed.py tests/api/test_intel_api.py -v
```

前端：

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend && bash scripts/lint.sh
```

手动：

- 新 dashboard 默认打开
- legacy dashboard 可访问
- overview / source 切换正常
- seed 数据和 xhs 数据都可读

- [ ] **Step 4: 提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add README.md CLAUDE.md frontend/README.md docs/superpowers/plans/2026-05-19-operations-intel-dashboard-real-sources.md
git commit -m "docs: document operations dashboard workflow and next phase"
```

---

## Spec coverage 自检

- `按来源组织`: Task 6 / Task 7 覆盖三栏布局和来源导航
- `总览页轻量入口`: Task 6 / Task 7 的 `OverviewPanel` 覆盖
- `来源详情页深读`: Task 6 / Task 8 覆盖
- `总览页 1 句摘要 / 来源页 2-3 句摘要`: Task 4 / Task 6 / Task 7 覆盖
- `大学官网混合模式`: Task 3 seed 数据 + Task 8 差异化模块覆盖
- `右侧轻辅助栏`: Task 6 / Task 8 覆盖
- `空状态 / 异常状态 / 摘要缺失`: Task 6 组件壳 + Task 8 文案覆盖
- `去原文`: Task 6 的 `IntelCard` 覆盖
- `保留旧 dashboard`: Task 1 覆盖

没有遗漏 spec 的强约束。
