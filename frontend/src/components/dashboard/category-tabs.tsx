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
