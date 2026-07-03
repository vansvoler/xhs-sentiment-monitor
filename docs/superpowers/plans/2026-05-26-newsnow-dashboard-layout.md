# News Now Dashboard Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `/dashboard` into a News Now style source-tile overview while preserving source navigation and live intel APIs.

**Architecture:** Keep the existing client-side data loading in `dashboard/page.tsx`, but replace the overview and source-detail presentation components. Add small focused components for dashboard chrome, source tiles, ranked rows, and compact source panels. Do all data derivation in frontend helpers from the existing `IntelOverviewResponse`, `IntelSourceResponse`, and `IntelSourceSyncReport` shapes; do not change backend contracts.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, lucide-react, existing `/api/intel/*` endpoints

---

## File Structure

- Create: `frontend/src/components/operations-dashboard/dashboard-shell.tsx`
  - Owns page-level layout: left nav, top bar, main content, helper rail.
- Create: `frontend/src/components/operations-dashboard/newsnow-overview.tsx`
  - Renders the News Now style tile wall from overview data and university sync reports.
- Create: `frontend/src/components/operations-dashboard/source-tile.tsx`
  - Renders one colored source tile with ranked rows.
- Create: `frontend/src/components/operations-dashboard/ranked-intel-row.tsx`
  - Renders a compact numbered intel item row.
- Create: `frontend/src/components/operations-dashboard/source-ranked-panel.tsx`
  - Renders compact source detail lists, replacing large card flow.
- Modify: `frontend/src/app/dashboard/page.tsx`
  - Replace page shell markup with `DashboardShell`.
  - Use `NewsNowOverview` for overview state.
  - Use `SourceRankedPanel` for source state.
- Modify: `frontend/src/components/operations-dashboard/helper-rail.tsx`
  - Make the helper rail denser and fit the new shell.
- Modify: `frontend/src/components/operations-dashboard/sidebar.tsx`
  - Restyle navigation to match the News Now dark rail.
- Modify: `frontend/src/components/operations-dashboard/source-panel.tsx`
  - Either delegate to `SourceRankedPanel` or remove from page usage.
- Modify: `frontend/src/components/operations-dashboard/source-sections/university-section.tsx`
  - Compress sync cards into a status strip if still used.

## Task 1: Add Layout Shell

**Files:**
- Create: `frontend/src/components/operations-dashboard/dashboard-shell.tsx`
- Modify: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: Create `DashboardShell`**

Implement this component:

```tsx
import type { ReactNode } from "react";

import type { IntelHelperRail, IntelSourceKey, SourceNavItem } from "@/types";

import { OperationsHelperRail } from "./helper-rail";
import { OperationsSidebar } from "./sidebar";

interface DashboardShellProps {
  items: SourceNavItem[];
  activeKey: IntelSourceKey;
  helperRail: IntelHelperRail | null;
  onChange: (key: IntelSourceKey) => void;
  children: ReactNode;
}

export function DashboardShell({
  items,
  activeKey,
  helperRail,
  onChange,
  children,
}: DashboardShellProps) {
  return (
    <div className="min-h-screen bg-[#141517] text-[#f4f4f5]">
      <main className="mx-auto flex min-h-screen max-w-[1920px] gap-4 px-4 py-4">
        <OperationsSidebar items={items} activeKey={activeKey} onChange={onChange} />
        <section className="min-w-0 flex-1 space-y-4">{children}</section>
        <OperationsHelperRail data={helperRail} />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Wire the shell into `dashboard/page.tsx`**

Replace the outer `<div><main>...` structure with:

```tsx
<DashboardShell
  items={navItems}
  activeKey={activeKey}
  helperRail={overview?.helper_rail ?? sourceData?.helper_rail ?? null}
  onChange={handleSourceChange}
>
  {status === "loading" && <OperationsLoadingState />}
  {status === "error" && <OperationsErrorState />}
  {status === "ready" && overview && (
    <OverviewPanel
      data={overview}
      universitySyncReports={universitySyncReports}
    />
  )}
  {status === "ready" && sourceData && <SourcePanel data={sourceData} />}
</DashboardShell>
```

Also import:

```tsx
import { DashboardShell } from "@/components/operations-dashboard/dashboard-shell";
```

- [ ] **Step 3: Run frontend checks**

Run:

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend
bash scripts/lint.sh
./node_modules/.bin/tsc --noEmit
```

Expected: both pass.

## Task 2: Build News Now Tiles

**Files:**
- Create: `frontend/src/components/operations-dashboard/ranked-intel-row.tsx`
- Create: `frontend/src/components/operations-dashboard/source-tile.tsx`
- Create: `frontend/src/components/operations-dashboard/newsnow-overview.tsx`
- Modify: `frontend/src/components/operations-dashboard/overview-panel.tsx`

- [ ] **Step 1: Create `RankedIntelRow`**

```tsx
import type { IntelItem } from "@/types";

interface RankedIntelRowProps {
  item: IntelItem;
  rank: number;
  compact?: boolean;
}

export function RankedIntelRow({ item, rank, compact = false }: RankedIntelRowProps) {
  const primaryTarget = item.impact_targets[0];

  return (
    <a
      className="grid grid-cols-[24px_1fr] gap-2 rounded-md px-2 py-2 text-left transition-colors hover:bg-white/8"
      href={item.original_url}
      target="_blank"
      rel="noreferrer"
    >
      <span className="rounded bg-white/10 py-0.5 text-center text-[11px] font-medium text-white/70">
        {rank}
      </span>
      <span className="min-w-0">
        <span
          className={`block text-white ${
            compact ? "line-clamp-1 text-xs" : "line-clamp-2 text-sm"
          }`}
        >
          {item.title}
        </span>
        {primaryTarget ? (
          <span className="mt-1 inline-flex rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-white/60">
            {primaryTarget}
          </span>
        ) : null}
      </span>
    </a>
  );
}
```

- [ ] **Step 2: Create `SourceTile`**

```tsx
import { MoreVertical, RefreshCcw, Star } from "lucide-react";

import type { IntelItem, IntelSourceFeedKey } from "@/types";

import { RankedIntelRow } from "./ranked-intel-row";

const TILE_STYLES: Record<IntelSourceFeedKey, string> = {
  ucas: "from-[#425f8e] to-[#263a55]",
  university_site: "from-[#3d7a4d] to-[#24472d]",
  exam_board: "from-[#4d5561] to-[#30353d]",
  visa_policy: "from-[#884448] to-[#482427]",
  wechat_media: "from-[#5a5d63] to-[#363940]",
};

const SOURCE_INITIALS: Record<IntelSourceFeedKey, string> = {
  ucas: "U",
  university_site: "校",
  exam_board: "考",
  visa_policy: "签",
  wechat_media: "媒",
};

interface SourceTileProps {
  sourceKey: IntelSourceFeedKey;
  title: string;
  subtitle: string;
  items: IntelItem[];
  onOpen: (sourceKey: IntelSourceFeedKey) => void;
}

export function SourceTile({
  sourceKey,
  title,
  subtitle,
  items,
  onOpen,
}: SourceTileProps) {
  const visibleItems = items.slice(0, 8);

  return (
    <article className={`rounded-[10px] bg-gradient-to-b ${TILE_STYLES[sourceKey]} p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]`}>
      <header className="mb-3 flex items-center justify-between gap-3">
        <button
          className="flex min-w-0 items-center gap-2 text-left"
          onClick={() => onOpen(sourceKey)}
          type="button"
        >
          <span className="grid size-7 shrink-0 place-items-center rounded-full bg-white text-xs font-bold text-[#111318]">
            {SOURCE_INITIALS[sourceKey]}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-white">{title}</span>
            <span className="block truncate text-[11px] text-white/60">{subtitle}</span>
          </span>
        </button>
        <div className="flex items-center gap-1 text-white/35">
          <RefreshCcw className="size-4" />
          <Star className="size-4" />
          <MoreVertical className="size-4" />
        </div>
      </header>

      <div className="min-h-[250px] rounded-lg bg-black/35 p-1">
        {visibleItems.length === 0 ? (
          <div className="grid h-full min-h-[220px] place-items-center rounded-md border border-dashed border-white/10 text-xs text-white/45">
            今日暂无新增
          </div>
        ) : (
          visibleItems.map((item, index) => (
            <RankedIntelRow key={item.item_id} item={item} rank={index + 1} compact />
          ))
        )}
      </div>
    </article>
  );
}
```

- [ ] **Step 3: Create `NewsNowOverview`**

```tsx
import type {
  IntelOverviewResponse,
  IntelSourceFeedKey,
  IntelSourceSyncReport,
} from "@/types";

import { SourceTile } from "./source-tile";

const SOURCE_SUBTITLES: Record<IntelSourceFeedKey, string> = {
  ucas: "政策与申请节点",
  university_site: "重点学校官网动态",
  exam_board: "考试安排与成绩政策",
  visa_policy: "签证规则与材料要求",
  wechat_media: "媒体与垂类解读",
};

interface NewsNowOverviewProps {
  data: IntelOverviewResponse;
  universitySyncReports: IntelSourceSyncReport[];
  onOpenSource: (sourceKey: IntelSourceFeedKey) => void;
}

export function NewsNowOverview({
  data,
  universitySyncReports,
  onOpenSource,
}: NewsNowOverviewProps) {
  const universityReportCount = universitySyncReports.length;

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[#71717a]">
            Intelligence Radar
          </p>
          <h1 className="mt-1 text-xl font-semibold text-white">News Now 留学情报</h1>
        </div>
        <div className="flex rounded-full border border-white/10 bg-[#211b1d] p-1 text-xs">
          <span className="rounded-full bg-white/10 px-3 py-1 text-white">最新</span>
          <span className="px-3 py-1 text-[#71717a]">最热</span>
          <span className="px-3 py-1 text-[#71717a]">待读</span>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {data.sections.map((section) => (
          <SourceTile
            key={section.source_key}
            sourceKey={section.source_key}
            title={section.source_label}
            subtitle={
              section.source_key === "university_site" && universityReportCount > 0
                ? `${universityReportCount} 个学校同步状态`
                : SOURCE_SUBTITLES[section.source_key]
            }
            items={section.preview_items}
            onOpen={onOpenSource}
          />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Replace `OverviewPanel` body**

In `overview-panel.tsx`, replace the current stat cards and vertical section list with:

```tsx
import type { IntelOverviewResponse, IntelSourceFeedKey, IntelSourceSyncReport } from "@/types";

import { NewsNowOverview } from "./newsnow-overview";

export function OverviewPanel({
  data,
  universitySyncReports,
  onOpenSource,
}: {
  data: IntelOverviewResponse;
  universitySyncReports: IntelSourceSyncReport[];
  onOpenSource: (sourceKey: IntelSourceFeedKey) => void;
}) {
  return (
    <NewsNowOverview
      data={data}
      universitySyncReports={universitySyncReports}
      onOpenSource={onOpenSource}
    />
  );
}
```

- [ ] **Step 5: Pass `handleSourceChange` from page**

In `dashboard/page.tsx`, update overview render to:

```tsx
<OverviewPanel
  data={overview}
  universitySyncReports={universitySyncReports}
  onOpenSource={handleSourceChange}
/>
```

- [ ] **Step 6: Run frontend checks**

Run:

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend
bash scripts/lint.sh
./node_modules/.bin/tsc --noEmit
```

Expected: both pass.

## Task 3: Convert Source Details to Ranked Lists

**Files:**
- Create: `frontend/src/components/operations-dashboard/source-ranked-panel.tsx`
- Modify: `frontend/src/components/operations-dashboard/source-panel.tsx`
- Modify: `frontend/src/components/operations-dashboard/source-sections/university-section.tsx`

- [ ] **Step 1: Create `SourceRankedPanel`**

```tsx
import type { IntelItem, IntelSourceFeedKey, IntelSourceResponse } from "@/types";

import { RankedIntelRow } from "./ranked-intel-row";
import { SourceHeader } from "./source-header";

function SourceDetailRow({ item, rank }: { item: IntelItem; rank: number }) {
  const targets = item.impact_targets.slice(0, 2);

  return (
    <a
      className="grid grid-cols-[34px_1fr_auto] gap-3 rounded-lg px-3 py-3 text-left transition-colors hover:bg-white/6"
      href={item.original_url}
      target="_blank"
      rel="noreferrer"
    >
      <span className="rounded bg-white/10 py-1 text-center text-xs font-semibold text-white/70">
        {rank}
      </span>
      <span className="min-w-0">
        <span className="block line-clamp-2 text-sm font-medium text-white">{item.title}</span>
        <span className="mt-1 block line-clamp-1 text-xs text-[#a1a1aa]">
          {item.school_name ?? item.source_name}
        </span>
      </span>
      <span className="hidden items-center gap-1 md:flex">
        {targets.map((target) => (
          <span key={target} className="rounded bg-white/10 px-2 py-1 text-[11px] text-white/60">
            {target}
          </span>
        ))}
      </span>
    </a>
  );
}

function UniversitySyncStrip({ data }: { data: IntelSourceResponse }) {
  if (data.source_key !== "university_site" || data.sync_reports.length === 0) {
    return null;
  }

  const counts = data.sync_reports.reduce(
    (acc, report) => ({ ...acc, [report.status]: acc[report.status] + 1 }),
    { success: 0, blocked: 0, error: 0 },
  );

  return (
    <div className="grid gap-2 md:grid-cols-3">
      <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
        正常 {counts.success}
      </div>
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
        被拦截 {counts.blocked}
      </div>
      <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
        失败 {counts.error}
      </div>
    </div>
  );
}

export function SourceRankedPanel({ data }: { data: IntelSourceResponse }) {
  return (
    <section className="space-y-4">
      <SourceHeader sourceKey={data.source_key as IntelSourceFeedKey} itemCount={data.items.length} />
      <UniversitySyncStrip data={data} />
      <div className="rounded-[10px] border border-white/10 bg-[#1b1e23] p-2">
        {data.items.length === 0 ? (
          <div className="grid min-h-[260px] place-items-center rounded-lg border border-dashed border-white/10 text-sm text-[#71717a]">
            今日暂无新增
          </div>
        ) : (
          data.items.map((item, index) => (
            <SourceDetailRow key={item.item_id} item={item} rank={index + 1} />
          ))
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Route all source pages through ranked panel**

Replace `SourcePanel` with:

```tsx
import type { IntelSourceResponse } from "@/types";

import { SourceRankedPanel } from "./source-ranked-panel";

export function SourcePanel({ data }: { data: IntelSourceResponse }) {
  return <SourceRankedPanel data={data} />;
}
```

- [ ] **Step 3: Keep old source section files untouched**

Do not delete `ucas-section.tsx`, `university-section.tsx`, or `wechat-section.tsx` in this task. They are unused after `SourcePanel` switches to `SourceRankedPanel`, and can be removed in a later cleanup commit.

- [ ] **Step 4: Run frontend checks**

Run:

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend
bash scripts/lint.sh
./node_modules/.bin/tsc --noEmit
```

Expected: both pass.

## Task 4: Polish Navigation and Helper Rail

**Files:**
- Modify: `frontend/src/components/operations-dashboard/sidebar.tsx`
- Modify: `frontend/src/components/operations-dashboard/helper-rail.tsx`

- [ ] **Step 1: Restyle sidebar**

Update `OperationsSidebar` to use the News Now style rail:

```tsx
return (
  <aside className="hidden w-56 shrink-0 rounded-[10px] border border-white/10 bg-[#101114] p-4 lg:block">
    <div className="mb-5 flex items-center gap-3">
      <div className="grid size-9 place-items-center rounded-md bg-[#f04444] text-[11px] font-bold text-white">
        AI
      </div>
      <div>
        <p className="text-sm font-bold leading-none text-white">News</p>
        <p className="text-sm font-bold leading-none text-white">Now</p>
      </div>
    </div>
    <nav className="space-y-1">
      {items.map((item) => {
        const isActive = item.key === activeKey;

        return (
          <button
            key={item.key}
            onClick={() => onChange(item.key)}
            className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
              isActive
                ? "bg-white/10 text-white"
                : "text-[#a1a1aa] hover:bg-white/6 hover:text-white"
            }`}
          >
            {item.label}
          </button>
        );
      })}
    </nav>
  </aside>
);
```

- [ ] **Step 2: Restyle helper rail**

Make `OperationsHelperRail` denser:

```tsx
return (
  <aside className="hidden w-64 shrink-0 rounded-[10px] border border-white/10 bg-[#101114] px-4 py-5 xl:block">
    <div className="space-y-5">
      <div>
        <p className="text-xs text-[#71717a]">今日重点</p>
        <p className="mt-1 text-3xl font-semibold text-white">{data.highlight_count}</p>
      </div>
      <div>
        <p className="text-xs text-[#71717a]">影响对象</p>
        <div className="mt-3 space-y-2">
          {Object.entries(data.top_counts).map(([label, count]) => (
            <div key={label} className="flex items-center justify-between rounded-md bg-white/5 px-3 py-2 text-sm text-[#d4d4d8]">
              <span>{label}</span>
              <span className="text-white">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </aside>
);
```

- [ ] **Step 3: Run frontend checks**

Run:

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend
bash scripts/lint.sh
./node_modules/.bin/tsc --noEmit
```

Expected: both pass.

## Task 5: Final Verification

**Files:**
- No new edits unless verification fails.

- [ ] **Step 1: Run frontend static checks**

Run:

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend
bash scripts/lint.sh
./node_modules/.bin/tsc --noEmit
```

Expected: both pass.

- [ ] **Step 2: Try production build**

Run:

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend
npm run build
```

Expected: PASS outside restricted sandbox. If sandbox blocks Turbopack port binding with `Operation not permitted`, record that exact limitation and rely on lint + TypeScript checks.

- [ ] **Step 3: Run backend regression tests**

Run:

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/backend
UV_CACHE_DIR=.uv-cache bash scripts/test.sh -v
```

Expected: PASS. Backend was not intentionally changed by this plan, but the current branch includes backend work, so run it before handoff.

- [ ] **Step 4: Report manual browser limitation**

If local server launch still fails under sandbox port restrictions, state that browser verification could not be completed from Codex and provide the local URL:

```text
http://localhost:3000/dashboard
```

## Self-Review

- Spec coverage:
  - Total overview tile wall: Task 2.
  - Source navigation retained: Task 1 and Task 4.
  - Compact source details: Task 3.
  - University sync status compression: Task 3.
  - Responsive constraints: Task 1 shell and Task 2 tile grid use responsive Tailwind tracks.
- Placeholder scan:
  - No TODO/TBD/fill-later steps.
- Type consistency:
  - Uses existing `IntelOverviewResponse`, `IntelSourceResponse`, `IntelSourceFeedKey`, and `IntelSourceSyncReport`.
  - New components only accept existing frontend types.

