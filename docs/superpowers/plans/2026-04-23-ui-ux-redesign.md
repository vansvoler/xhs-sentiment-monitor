# UI/UX 重设计实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Dashboard 从原始深色风格升级为 Linear/Vercel 式现代极简风，修复文字对比度，统一品牌蓝配色语义。

**Architecture:** 纯视觉层改动，不触及业务逻辑。从 CSS 变量系统出发，向上逐层替换颜色引用；所有改动以组件为单位，每个 Task 对应一个文件或一组紧密相关的文件。

**Tech Stack:** Next.js 16, React 19, Tailwind CSS 4, Recharts, TypeScript

---

## 文件变更地图

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/app/globals.css` | Modify | CSS 变量系统全量重写 |
| `frontend/src/lib/utils.ts` | Modify | `SENTIMENT_CONFIG` 颜色更新 |
| `frontend/src/components/ui/badge.tsx` | Modify | `TagBadge` 颜色变量化 |
| `frontend/src/components/ui/card.tsx` | Modify | 背景/圆角/CardTitle 颜色 |
| `frontend/src/components/dashboard/header.tsx` | Modify | Logo 品牌蓝 + 副标题 + border |
| `frontend/src/components/dashboard/stats-overview.tsx` | Modify | 数字语义颜色 + 环比指示 |
| `frontend/src/components/dashboard/category-tabs.tsx` | Modify | 选中态改品牌蓝；情感筛选颜色 |
| `frontend/src/app/dashboard/page.tsx` | Modify | 趋势天数按钮选中态 + gap 调整 |
| `frontend/src/components/charts/sentiment-donut.tsx` | Modify | tooltip 颜色变量化 |
| `frontend/src/components/charts/trend-line.tsx` | Modify | 负面线/渐变从 #ef4444 改 #f87171；中性线从 #94a3b8 改 #52525b |
| `frontend/src/components/charts/competitor-bar.tsx` | Modify | 负面柱从 #ef4444 改 #f87171 |

---

## Task 1: CSS 变量系统重写

**Files:**
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: 替换 globals.css 中的 @theme 变量块**

将文件中 `@theme inline { ... }` 块整体替换为以下内容（字体部分不动）：

```css
@theme inline {
  /* ── 背景色 ── */
  --color-background:        #09090b;
  --color-surface:           #111113;
  --color-surface-elevated:  #18181b;
  --color-border:            #27272a;
  --color-border-muted:      #1c1c1f;

  /* ── 文字色（WCAG AA 全部通过）── */
  --color-text-primary:      #ffffff;
  --color-text-body:         #f4f4f5;
  --color-text-secondary:    #a1a1aa;
  --color-text-muted:        #71717a;

  /* ── 品牌色（深宝蓝，替换旧品牌红）── */
  --color-brand:             #1e51a2;
  --color-brand-hover:       #1a4690;
  --color-brand-muted:       rgba(30, 81, 162, 0.12);

  /* ── 情感色（收敛为 3 色，移除蓝/橙）── */
  --color-positive:          #22c55e;
  --color-positive-muted:    rgba(34, 197, 94, 0.1);
  --color-negative:          #f87171;
  --color-negative-muted:    rgba(248, 113, 113, 0.1);
  --color-neutral:           #52525b;
  --color-neutral-muted:     rgba(82, 82, 91, 0.15);

  /* ── 字体（不变）── */
  --font-sans: 'Fira Sans', system-ui, sans-serif;
  --font-mono: 'Fira Code', monospace;
}
```

- [ ] **Step 2: 更新 body 默认色和 focus-visible 颜色**

将 `globals.css` 中以下两处硬编码颜色替换：

```css
/* 旧 */
body {
  background: #0a0a0a;
  color: #f5f5f5;
  ...
}
:focus-visible {
  outline: 2px solid #e11d48;
  ...
}

/* 新 */
body {
  background: var(--color-background);
  color: var(--color-text-body);
  ...
}
:focus-visible {
  outline: 2px solid var(--color-brand);
  ...
}
```

- [ ] **Step 3: 启动前端，检查页面不崩溃**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend && npm run dev
```

打开 http://localhost:3000，页面应正常渲染（颜色变化不明显，因为各组件仍用硬编码颜色，后续 Task 逐步替换）。

- [ ] **Step 4: 提交**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor
git add frontend/src/app/globals.css
git commit -m "style: 重写 CSS 变量系统，引入品牌蓝和强对比文字层级"
```

---

## Task 2: 情感配色基础层（utils + badge）

**Files:**
- Modify: `frontend/src/lib/utils.ts`
- Modify: `frontend/src/components/ui/badge.tsx`

- [ ] **Step 1: 更新 utils.ts 中的 SENTIMENT_CONFIG**

将 `SENTIMENT_CONFIG` 替换为：

```ts
export const SENTIMENT_CONFIG: Record<
  SentimentLabel,
  { label: string; color: string; bgColor: string; textColor: string }
> = {
  positive: {
    label: "正面",
    color: "#22c55e",
    bgColor: "rgba(34,197,94,0.1)",
    textColor: "#22c55e",
  },
  negative: {
    label: "负面",
    color: "#f87171",
    bgColor: "rgba(248,113,113,0.1)",
    textColor: "#f87171",
  },
  neutral: {
    label: "中性",
    color: "#52525b",
    bgColor: "rgba(82,82,91,0.15)",
    textColor: "#a1a1aa",
  },
};
```

> 注意：neutral 的 `textColor` 用 `#a1a1aa`（次要文字色），比 `color` (#52525b) 更亮，确保 badge 内文字对比度达标。

- [ ] **Step 2: 更新 badge.tsx 中的 TagBadge 硬编码颜色**

将 `TagBadge` 组件替换为：

```tsx
export function TagBadge({ children }: TagBadgeProps) {
  return (
    <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs bg-[#18181b] text-[#a1a1aa] border border-[#27272a]">
      {children}
    </span>
  );
}
```

> `SentimentBadge` 不需要改，它已经读 `SENTIMENT_CONFIG`，更新 config 即生效。

- [ ] **Step 3: 验证 badge 颜色**

在浏览器中找到任意有情感标签的笔记行，确认：
- 正面 badge：绿色文字 + 绿色浅背景
- 负面 badge：柔红文字（`#f87171`，非刺眼的 `#ef4444`）+ 柔红浅背景
- 中性 badge：灰色文字 + 灰色浅背景

- [ ] **Step 4: 提交**

```bash
git add frontend/src/lib/utils.ts frontend/src/components/ui/badge.tsx
git commit -m "style: 情感色收敛为柔红/绿/灰，TagBadge 颜色变量化"
```

---

## Task 3: Card 组件升级

**Files:**
- Modify: `frontend/src/components/ui/card.tsx`

- [ ] **Step 1: 更新 Card、CardTitle 颜色和圆角**

将整个 `card.tsx` 替换为：

```tsx
import type { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
}

export function Card({ elevated, className = "", children, ...props }: CardProps) {
  const bg = elevated ? "bg-[#18181b]" : "bg-[#111113]";
  return (
    <div
      className={`rounded-[10px] border border-[#27272a] ${bg} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className = "", children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`flex items-center justify-between px-5 py-4 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className = "", children, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={`text-sm font-medium text-[#f4f4f5] ${className}`} {...props}>
      {children}
    </h3>
  );
}

export function CardContent({ className = "", children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`px-5 pb-5 ${className}`} {...props}>
      {children}
    </div>
  );
}
```

> 变更点：圆角 `rounded-xl`(12px) → `rounded-[10px]`；CardTitle 从 `#d4d4d4` 升为 `#f4f4f5`；surface-elevated 从 `#1a1a1a` 对齐新变量 `#18181b`。

- [ ] **Step 2: 验证**

刷新浏览器，所有卡片标题应更亮白，圆角略小但更精致。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/ui/card.tsx
git commit -m "style: Card 圆角统一 10px，CardTitle 对比度提升"
```

---

## Task 4: Header 重设计

**Files:**
- Modify: `frontend/src/components/dashboard/header.tsx`

- [ ] **Step 1: 更新 header.tsx**

将整个 `header.tsx` 替换为：

```tsx
"use client";

import { Activity } from "lucide-react";
import type { ConnectionStatus } from "@/lib/websocket";

interface HeaderProps {
  wsStatus: ConnectionStatus;
  keywords: string[];
}

const STATUS_CONFIG: Record<ConnectionStatus, { label: string; color: string }> = {
  connecting: { label: "连接中", color: "#f59e0b" },
  connected:  { label: "实时",   color: "#22c55e" },
  disconnected: { label: "已断线", color: "#f87171" },
};

const MAX_VISIBLE = 8;

export function DashboardHeader({ wsStatus, keywords }: HeaderProps) {
  const cfg = STATUS_CONFIG[wsStatus];
  const visible = keywords.slice(0, MAX_VISIBLE);
  const overflow = keywords.length - MAX_VISIBLE;

  return (
    <header className="sticky top-0 z-40 border-b border-[#27272a] bg-[#09090b]/90 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-screen-2xl items-center justify-between px-6">
        {/* 品牌 */}
        <div className="flex items-center gap-3">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ background: "linear-gradient(135deg, #1e51a2, #2563eb)" }}
          >
            <Activity size={15} className="text-white" aria-hidden="true" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold leading-tight text-[#ffffff]">
              小红书舆情监控
            </span>
            <span className="text-[10px] leading-tight text-[#71717a]">
              小红书品牌分析
            </span>
          </div>
        </div>

        {/* 监控关键词 */}
        {visible.length > 0 && (
          <div className="hidden md:flex items-center gap-1.5" aria-label="监控关键词">
            <span className="text-xs text-[#71717a]">监控：</span>
            <div className="flex flex-wrap gap-1">
              {visible.map((kw) => (
                <span
                  key={kw}
                  className="rounded px-1.5 py-0.5 text-xs bg-[#18181b] text-[#a1a1aa] border border-[#27272a]"
                >
                  {kw}
                </span>
              ))}
              {overflow > 0 && (
                <span className="rounded px-1.5 py-0.5 text-xs bg-[#18181b] text-[#71717a] border border-[#27272a]">
                  +{overflow}
                </span>
              )}
            </div>
          </div>
        )}

        {/* 实时状态 */}
        <div
          className="flex items-center gap-1.5 rounded-full border border-[#27272a] bg-[#111113] px-3 py-1"
          role="status"
          aria-label={`WebSocket 状态：${cfg.label}`}
        >
          <span
            className="h-2 w-2 rounded-full animate-pulse-dot"
            style={{ background: cfg.color }}
            aria-hidden="true"
          />
          <span className="text-xs text-[#a1a1aa]">{cfg.label}</span>
        </div>
      </div>
    </header>
  );
}
```

> 变更点：Logo 从红色改为品牌蓝渐变；增加副标题；border 颜色对齐新变量；断线状态从 `#ef4444` 改 `#f87171`；文字颜色全部对齐新层级。

- [ ] **Step 2: 验证 Header**

刷新浏览器，确认：
- Logo 方块显示品牌蓝渐变（深蓝→蓝）
- Logo 右侧有两行文字：「小红书舆情监控」（白）和「小红书品牌分析」（灰）
- 顶部 border 可见（比原来更明显）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/dashboard/header.tsx
git commit -m "style: Header 换品牌蓝 Logo，增加副标题，修复文字对比度"
```

---

## Task 5: Stats Overview 升级

**Files:**
- Modify: `frontend/src/components/dashboard/stats-overview.tsx`

- [ ] **Step 1: 更新 stats-overview.tsx**

将整个文件替换为：

```tsx
"use client";

import { FileText, TrendingUp, ThumbsUp, AlertTriangle } from "lucide-react";
import type { NotesSummary } from "@/types";
import { formatNumber } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { SkeletonCard } from "@/components/ui/skeleton";

interface StatsOverviewProps {
  summary: NotesSummary | null;
  loading: boolean;
}

export function StatsOverview({ summary, loading }: StatsOverviewProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  const dist = summary?.sentiment_distribution ?? {};
  const positiveCount = dist.positive ?? 0;
  const totalSentiment =
    (dist.positive ?? 0) + (dist.negative ?? 0) + (dist.neutral ?? 0);
  const positiveRate =
    totalSentiment > 0
      ? ((positiveCount / totalSentiment) * 100).toFixed(1)
      : "—";

  const cards = [
    {
      icon: FileText,
      label: "累计笔记",
      value: formatNumber(summary?.total_notes ?? 0),
      sub: "全量采集",
      valueColor: "#1e51a2",
      bg: "rgba(30,81,162,0.1)",
      iconColor: "#1e51a2",
    },
    {
      icon: TrendingUp,
      label: "今日新增",
      value: formatNumber(summary?.today_notes ?? 0),
      sub: "过去 24h",
      valueColor: "#1e51a2",
      bg: "rgba(30,81,162,0.1)",
      iconColor: "#1e51a2",
    },
    {
      icon: ThumbsUp,
      label: "正面率",
      value: positiveRate === "—" ? "—" : `${positiveRate}%`,
      sub: `共 ${totalSentiment} 条已分析`,
      valueColor: "#22c55e",
      bg: "rgba(34,197,94,0.1)",
      iconColor: "#22c55e",
    },
    {
      icon: AlertTriangle,
      label: "负面笔记",
      value: formatNumber(summary?.sentiment_distribution?.negative ?? 0),
      sub: "需关注",
      valueColor: "#f87171",
      bg: "rgba(248,113,113,0.1)",
      iconColor: "#f87171",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((c) => {
        const Icon = c.icon;
        return (
          <Card key={c.label} className="p-[14px]">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-[#71717a] mb-2 tracking-wide">{c.label}</p>
                <p
                  className="font-mono text-[22px] font-bold leading-none"
                  style={{ color: c.valueColor, letterSpacing: "-1px" }}
                >
                  {c.value}
                </p>
                <p className="mt-2 text-xs text-[#71717a]">{c.sub}</p>
              </div>
              <div
                className="flex h-9 w-9 items-center justify-center rounded-lg flex-shrink-0"
                style={{ background: c.bg }}
              >
                <Icon size={16} style={{ color: c.iconColor }} aria-hidden="true" />
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
```

> 变更点：「累计笔记」和「今日新增」从蓝/红改为品牌蓝；「负面笔记」从橙改为柔红；数字字号 `text-2xl` → `text-[22px]`；`letter-spacing: -1px`；gap 从 `gap-3` 改 `gap-4`；内边距 `p-5` 改 `p-[14px]`。

- [ ] **Step 2: 验证统计卡片**

刷新浏览器，确认 4 张卡片：
- 「累计笔记」「今日新增」数字为品牌蓝（深蓝）
- 「正面率」数字为绿色
- 「负面笔记」数字为柔红（非刺眼红）
- 数字更大、更醒目

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/dashboard/stats-overview.tsx
git commit -m "style: Stats 卡片数字语义配色，品牌蓝/绿/柔红，字号加大"
```

---

## Task 6: CategoryTabs + page.tsx 选中态

**Files:**
- Modify: `frontend/src/components/dashboard/category-tabs.tsx`
- Modify: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: 更新 category-tabs.tsx**

将整个文件替换为：

```tsx
"use client";

import type { CategoryType, SentimentFilter } from "@/types";

export type ActiveTab = CategoryType | "all";

interface CategoryTabsProps {
  active: ActiveTab;
  onChange: (tab: ActiveTab) => void;
}

const TABS: { value: ActiveTab; label: string }[] = [
  { value: "all",        label: "全部" },
  { value: "brand",      label: "品牌舆情" },
  { value: "competitor", label: "竞品监控" },
  { value: "industry",   label: "行业洞察" },
];

export function CategoryTabs({ active, onChange }: CategoryTabsProps) {
  return (
    <div className="flex gap-1" role="tablist" aria-label="监控分类">
      {TABS.map(({ value, label }) => (
        <button
          key={value}
          role="tab"
          aria-selected={active === value}
          onClick={() => onChange(value)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${
            active === value
              ? "bg-[#1e51a2] text-white"
              : "text-[#71717a] hover:bg-[#18181b] hover:text-[#f4f4f5]"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// ── 情感快捷筛选栏 ────────────────────────────────────────────────────────────

const SENTIMENT_TABS: { value: SentimentFilter; label: string; color?: string }[] = [
  { value: "all",      label: "全部情感" },
  { value: "positive", label: "正面", color: "#22c55e" },
  { value: "negative", label: "负面", color: "#f87171" },
  { value: "neutral",  label: "中性", color: "#52525b" },
];

interface SentimentBarProps {
  active: SentimentFilter;
  onChange: (s: SentimentFilter) => void;
}

export function SentimentBar({ active, onChange }: SentimentBarProps) {
  return (
    <div className="flex gap-1" role="group" aria-label="情感筛选">
      {SENTIMENT_TABS.map(({ value, label, color }) => (
        <button
          key={value}
          onClick={() => onChange(value)}
          aria-pressed={active === value}
          className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
            active === value
              ? "bg-[#18181b] text-[#f4f4f5]"
              : "text-[#71717a] hover:text-[#a1a1aa]"
          }`}
        >
          {color && (
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ background: color }}
              aria-hidden="true"
            />
          )}
          {label}
        </button>
      ))}
    </div>
  );
}
```

> 变更点：CategoryTabs 选中态从 `bg-[#e11d48]` 改为 `bg-[#1e51a2]`；SentimentBar 负面圆点从 `#ef4444` 改 `#f87171`；中性圆点从 `#94a3b8` 改 `#52525b`；hover 文字从 `#f5f5f5` 改 `#f4f4f5`。

- [ ] **Step 2: 更新 page.tsx 中趋势天数按钮的选中态**

在 `frontend/src/app/dashboard/page.tsx` 中，找到以下片段：

```tsx
className={`rounded px-2 py-0.5 text-xs transition-colors cursor-pointer ${
  trendDays === d
    ? "bg-[#e11d48] text-white"
    : "text-[#525252] hover:text-[#a3a3a3]"
}`}
```

替换为：

```tsx
className={`rounded px-2 py-0.5 text-xs transition-colors cursor-pointer ${
  trendDays === d
    ? "bg-[#1e51a2] text-white"
    : "text-[#71717a] hover:text-[#a1a1aa]"
}`}
```

同时将 `main` 标签上的 `space-y-6` 改为 `space-y-5`，`section` 之间的 `gap-4` 保持不变。

- [ ] **Step 3: 验证**

刷新浏览器，确认：
- 分类 Tab 选中态为品牌蓝，不再是红色
- 情感筛选负面圆点为柔红
- 趋势图右上角天数按钮选中为品牌蓝

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/dashboard/category-tabs.tsx frontend/src/app/dashboard/page.tsx
git commit -m "style: 选中态全部改品牌蓝，情感筛选颜色对齐新配色"
```

---

## Task 7: 图表颜色同步

**Files:**
- Modify: `frontend/src/components/charts/trend-line.tsx`
- Modify: `frontend/src/components/charts/competitor-bar.tsx`
- Modify: `frontend/src/components/charts/sentiment-donut.tsx`

- [ ] **Step 1: 更新 trend-line.tsx 中的颜色**

在 `trend-line.tsx` 中，做以下替换（3 处）：

1. `gradNegative` 渐变的 `stopColor`:
```tsx
/* 旧 */
<stop offset="5%"  stopColor="#ef4444" stopOpacity={0.3} />
<stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
/* 新 */
<stop offset="5%"  stopColor="#f87171" stopOpacity={0.3} />
<stop offset="95%" stopColor="#f87171" stopOpacity={0} />
```

2. `gradNeutral` 渐变的 `stopColor`:
```tsx
/* 旧 */
<stop offset="5%"  stopColor="#94a3b8" stopOpacity={0.2} />
<stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
/* 新 */
<stop offset="5%"  stopColor="#52525b" stopOpacity={0.2} />
<stop offset="95%" stopColor="#52525b" stopOpacity={0} />
```

3. `Area` 的 `stroke` 颜色：
```tsx
/* 旧 */
<Area ... dataKey="negative_count" stroke="#ef4444" ... />
<Area ... dataKey="neutral_count"  stroke="#94a3b8" ... />
/* 新 */
<Area ... dataKey="negative_count" stroke="#f87171" ... />
<Area ... dataKey="neutral_count"  stroke="#52525b" ... />
```

同时更新 Tooltip 和 Legend 中的硬编码颜色：
```tsx
/* Tooltip contentStyle */
background: "#18181b",   /* 旧 #1a1a1a */
border: "1px solid #27272a",  /* 旧 #252525 */
color: "#f4f4f5",        /* 旧 #f5f5f5 */

/* labelStyle */
color: "#a1a1aa",        /* 旧 #a3a3a3 */

/* Legend formatter */
<span className="text-xs text-[#a1a1aa]">  /* 旧 text-[#a3a3a3] */
```

- [ ] **Step 2: 更新 competitor-bar.tsx 中的颜色**

在 `competitor-bar.tsx` 中，做以下替换：

```tsx
/* 旧 */
<Bar dataKey="负面率" fill="#ef4444" ...>
  {formatted.map((_, i) => (
    <Cell key={i} fill="#ef4444" fillOpacity={0.85} />
  ))}
</Bar>

/* 新 */
<Bar dataKey="负面率" fill="#f87171" ...>
  {formatted.map((_, i) => (
    <Cell key={i} fill="#f87171" fillOpacity={0.85} />
  ))}
</Bar>
```

同时更新 Tooltip contentStyle：
```tsx
background: "#18181b",
border: "1px solid #27272a",
color: "#f4f4f5",
```

- [ ] **Step 3: 更新 sentiment-donut.tsx 中的 Tooltip 颜色**

`sentiment-donut.tsx` 中 `SENTIMENT_CONFIG` 已经通过 Task 2 更新生效（颜色从 utils.ts 读取），只需更新 Tooltip 和空状态文字：

```tsx
/* Tooltip contentStyle */
background: "#18181b",
border: "1px solid #27272a",
color: "#f4f4f5",

/* Legend formatter */
<span className="text-xs text-[#a1a1aa]">

/* 空状态 */
<div className="flex h-48 items-center justify-center text-[#71717a] text-sm">

/* 中心总数 */
<span className="font-mono text-2xl font-semibold text-[#ffffff]">
<span className="text-xs text-[#71717a]">总计</span>
```

- [ ] **Step 4: 验证图表**

刷新浏览器，在有数据的情况下确认：
- 情感趋势图：负面线为柔红（非刺眼红），中性线为深灰
- 竞品对比图：负面柱为柔红
- 情感分布环形图：负面扇区为柔红（通过 SENTIMENT_CONFIG 自动生效）
- 所有图表 tooltip 背景为 `#18181b`

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/charts/
git commit -m "style: 图表颜色统一，负面改柔红，中性改深灰，tooltip 颜色对齐"
```

---

## Task 8: 全局文字颜色残留清理

**Files:**
- Modify: `frontend/src/app/dashboard/page.tsx`

> 这一步清理 page.tsx 中仍残留的旧颜色硬编码，不涉及逻辑改动。

- [ ] **Step 1: 全局替换 page.tsx 中的旧颜色引用**

在 `page.tsx` 中做以下 find-and-replace（编辑器全局替换即可）：

| 旧值 | 新值 | 说明 |
|------|------|------|
| `text-[#525252]` | `text-[#71717a]` | 弱化文字升级 |
| `text-[#737373]` | `text-[#71717a]` | 刷新按钮文字 |
| `text-[#a3a3a3]` | `text-[#a1a1aa]` | 次要文字升级 |
| `text-[#f5f5f5]` | `text-[#f4f4f5]` | 主体文字对齐 |
| `hover:text-[#f5f5f5]` | `hover:text-[#f4f4f5]` | hover 态 |
| `bg-[#0a0a0a]` | `bg-[#09090b]` | 页面背景对齐 |
| `bg-[#1a1a1a]` | `bg-[#18181b]` | surface-elevated |
| `bg-[#1e1e1e]` | `bg-[#1c1c1f]` | border-muted |
| `border-[#1e1e1e]` | `border-[#1c1c1f]` | border-muted |

- [ ] **Step 2: 验证 page.tsx 中没有 #525252、#737373、#a3a3a3、#0a0a0a、#1a1a1a 残留**

```bash
grep -n "#525252\|#737373\|#a3a3a3\|#0a0a0a\|#1a1a1a\|#e11d48" \
  /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend/src/app/dashboard/page.tsx
```

预期输出：无匹配（空输出）。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/app/dashboard/page.tsx
git commit -m "style: page.tsx 文字和背景颜色全部对齐新变量值"
```

---

## Task 9: 端到端视觉验收

- [ ] **Step 1: 启动前端**

```bash
cd /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend && npm run dev
```

- [ ] **Step 2: 逐项视觉核对**

打开 http://localhost:3000，按以下清单逐项确认：

| 项目 | 预期 | 通过？ |
|------|------|--------|
| Header Logo | 品牌蓝渐变方块 + 两行文字 | |
| Header border | 底部有明显细线 | |
| 「累计笔记」数字 | 品牌蓝 #1e51a2 | |
| 「今日新增」数字 | 品牌蓝 #1e51a2 | |
| 「正面率」数字 | 绿色 #22c55e | |
| 「负面笔记」数字 | 柔红 #f87171（不刺眼） | |
| 分类 Tab 选中 | 品牌蓝背景白字（非红色） | |
| 情感筛选负面圆点 | 柔红 #f87171 | |
| 趋势图天数选中 | 品牌蓝背景（非红色） | |
| 负面情感 badge | 柔红文字 + 柔红浅背景 | |
| 正文笔记内容 | 接近白色 #f4f4f5，清晰可读 | |
| 时间戳/次要文字 | 灰色但清晰可见 #a1a1aa | |
| 趋势图负面线 | 柔红（非刺眼红） | |
| 竞品图负面柱 | 柔红 | |
| 卡片圆角 | 10px，略比原来小 | |

- [ ] **Step 3: 如发现遗漏的硬编码旧颜色，全局搜索并修复**

```bash
grep -rn "#e11d48\|#ef4444\|#94a3b8\|#3b82f6\|#f59e0b\|#525252\|#a3a3a3\|#f5f5f5\|#0a0a0a\|#141414\|#1a1a1a\|#252525\|#1e1e1e" \
  /Users/Vance/Coding/Projects/xhs-sentiment-monitor/frontend/src/
```

对每个命中文件按新变量值逐一修复，参照 Task 8 Step 1 的映射表。

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "style: UI/UX 重设计完成，品牌蓝配色 + WCAG AA 对比度"
```
