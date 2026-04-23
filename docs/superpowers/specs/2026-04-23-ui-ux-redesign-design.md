# UI/UX 重设计规格文档

**日期：** 2026-04-23  
**范围：** 前端 `frontend/src/` 视觉层全面升级，不涉及业务逻辑和布局结构

---

## 背景与目标

当前 Dashboard 存在三个核心问题：
1. **颜色太杂**：红/绿/蓝/橙/灰五种功能色并存，视觉没有重点
2. **文字对比度不足**：正文用 `#a3a3a3`，次要信息用 `#525252`，均低于 WCAG AA 标准
3. **视觉层级依赖颜色而非排版**：信息权重不清晰

目标：用 Linear/Vercel 风格的现代极简设计，通过排版和间距建立层级，颜色只表达语义。

---

## 设计决策

| 维度 | 决策 |
|------|------|
| 整体风格 | 现代极简（纯黑底 + 极细边框） |
| 版式密度 | 宽松克制（大数字 + 充足留白） |
| 品牌色 | `#1e51a2`（rgb 30/81/162 深宝蓝） |
| 情感色 | 绿 `#22c55e` / 柔红 `#f87171` / 灰 `#52525b` |
| 对比度标准 | WCAG AA（最低 4.5:1） |

---

## 1. CSS 变量系统重写

**文件：** `frontend/src/app/globals.css`

### 背景色（不变）

```css
--color-background:        #09090b;   /* 页面背景 */
--color-surface:           #111113;   /* 卡片背景 */
--color-surface-elevated:  #18181b;   /* 行 hover 背景 */
--color-border:            #27272a;   /* 主边框 */
--color-border-muted:      #1c1c1f;   /* 次要边框 / 行分隔 */
```

### 文字色（全部上调，修复对比度）

```css
--color-text-primary:      #ffffff;   /* 主标题 / 大数字  — 对比度 21:1 */
--color-text-body:         #f4f4f5;   /* 正文 / 笔记内容  — 对比度 19:1 */
--color-text-secondary:    #a1a1aa;   /* 次要信息 / 时间戳 — 对比度 7.2:1 */
--color-text-muted:        #71717a;   /* 标签 / placeholder — 对比度 4.6:1 */
```

> 移除旧的 `--color-text-primary: #f5f5f5` / `--color-text-secondary: #a3a3a3` / `--color-text-muted: #525252`  
> 新增 `--color-text-body`：旧代码中笔记正文、列表内容等使用 `--color-text-secondary` 的地方，实现时改引用 `--color-text-body`；`--color-text-secondary` 保留给时间戳等真正的次要信息。

### 品牌色（替换旧品牌红）

```css
--color-brand:             #1e51a2;   /* 品牌蓝 — 数量 KPI / Logo / 选中态 */
--color-brand-hover:       #1a4690;   /* hover 状态 */
--color-brand-muted:       rgba(30,81,162,0.12); /* 品牌色背景 */
```

> 移除旧的 `--color-primary: #e11d48` 系列（Logo 内部渐变保留）

### 情感色（收敛，移除蓝/橙）

```css
--color-positive:          #22c55e;   /* 正面情感 */
--color-positive-muted:    rgba(34,197,94,0.1);
--color-negative:          #f87171;   /* 负面情感（柔红，≠品牌红） */
--color-negative-muted:    rgba(248,113,113,0.1);
--color-neutral:           #52525b;   /* 中性情感 */
--color-neutral-muted:     rgba(82,82,91,0.15);
```

> 移除 `--color-accent: #3b82f6`（蓝）和 `--color-warning: #f59e0b`（橙）

---

## 2. Header 重设计

**文件：** `frontend/src/components/dashboard/header.tsx`

- Logo 方块：`background: linear-gradient(135deg, #1e51a2, #2563eb)`，圆角 8px，尺寸 30×30
- Logo 下增加副标题文字「小红书品牌分析」，颜色 `--color-text-muted`
- Header 底部加 `border-bottom: 1px solid var(--color-border)`
- 实时状态指示器保留，绿点颜色不变

---

## 3. Stats Overview 升级

**文件：** `frontend/src/components/dashboard/stats-overview.tsx`

- 卡片内边距：`padding: 14px`（原 12px）
- 卡片圆角：`border-radius: 10px`（原 8px）
- 数字字号：`font-size: 22px; font-weight: 700; letter-spacing: -1px`
- 数字颜色语义分配：
  - 「累计笔记」「今日新增」→ `var(--color-brand)` 品牌蓝
  - 「正面率」→ `var(--color-positive)` 绿色
  - 「负面预警」→ `var(--color-negative)` 柔红
- 每张卡片增加环比指示行（↑↓ + 百分比），颜色跟随正负方向

---

## 4. 情感色全局统一

**文件：** `frontend/src/lib/utils.ts`（`SENTIMENT_CONFIG`）、`frontend/src/components/ui/badge.tsx`

`SENTIMENT_CONFIG` 更新为：

```ts
export const SENTIMENT_CONFIG = {
  positive: { color: '#22c55e', bg: 'rgba(34,197,94,0.1)',  label: '正面' },
  negative: { color: '#f87171', bg: 'rgba(248,113,113,0.1)', label: '负面' },
  neutral:  { color: '#52525b', bg: 'rgba(82,82,91,0.15)',   label: '中性' },
}
```

`SentimentBadge` 直接读 `SENTIMENT_CONFIG`，不再硬编码颜色。

---

## 5. CategoryTabs 选中态

**文件：** `frontend/src/components/dashboard/category-tabs.tsx`

- 选中：`background: var(--color-brand); color: #ffffff; border-radius: 6px`
- 未选中：`background: var(--color-surface-elevated); color: var(--color-text-muted)`
- 移除旧的品牌红选中态

---

## 6. 卡片圆角 + 间距

全局统一：
- 所有 `Card` 组件圆角：`10px`
- 页面主区域 grid gap：`20px`（原 16px）
- 列表行内边距：`padding: 10px 14px`

---

## 7. 图表颜色同步

**文件：** `frontend/src/components/charts/`（三个文件）

| 图表 | 变更 |
|------|------|
| `sentiment-donut.tsx` | 三色改为 `#22c55e` / `#f87171` / `#52525b` |
| `trend-line.tsx` | 正面线 `#22c55e`，负面线 `#f87171`，中性线 `#52525b`；渐变 fill 对应更新 |
| `competitor-bar.tsx` | 正面柱 `#22c55e`，负面柱 `#f87171`；移除旧蓝/橙 |

---

## 不动的部分

- 整体网格布局结构
- 所有组件业务逻辑和数据流
- WebSocket 实时推送功能
- 骨架屏加载状态
- 响应式断点和移动端布局

---

## 验证方法

1. 启动前端：`cd frontend && npm run dev`
2. 打开 `http://localhost:3000`，逐项确认：
   - Header Logo 显示品牌蓝渐变
   - 统计卡片数字颜色符合语义分配（蓝/绿/红）
   - 正文笔记内容清晰可读（非灰色）
   - 时间戳等次要信息可见但不抢眼
   - 分类标签选中态为品牌蓝
   - 三个图表颜色统一
3. 使用浏览器无障碍工具（如 Chrome DevTools → Accessibility）验证对比度
