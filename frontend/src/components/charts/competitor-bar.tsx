"use client";

import type { CompetitorData } from "@/types";
import { formatNumber } from "@/lib/utils";

interface CompetitorBarProps {
  data: CompetitorData[];
}

interface CompetitorViewModel {
  name: string;
  isOwn: boolean;
  noteCount: number;
  totalMentions: number;
  positivePct: number;
  negativePct: number;
  neutralPct: number;
  netPct: number;
}

const OWN_BRAND_NAME = "渊学通";

function toPct(value: number): number {
  return Math.round(value * 1000) / 10;
}

function toRows(data: CompetitorData[]): CompetitorViewModel[] {
  return data
    .map((item) => {
      const positivePct = toPct(item.positive_rate);
      const negativePct = toPct(item.negative_rate);

      return {
        isOwn: !!item.is_own,
        name: item.is_own ? OWN_BRAND_NAME : item.name,
        noteCount: item.note_count,
        totalMentions: item.total_mentions,
        positivePct,
        negativePct,
        neutralPct: Math.max(0, 100 - positivePct - negativePct),
        netPct: positivePct - negativePct,
      };
    })
    .sort(
      (a, b) => Number(b.isOwn) - Number(a.isOwn) || b.noteCount - a.noteCount,
    );
}

function SentimentBar({ row }: { row: CompetitorViewModel }) {
  return (
    <div
      className="flex h-2.5 overflow-hidden rounded-full bg-[#eaeef4]"
      aria-label={`${row.name} 正面 ${row.positivePct}%，负面 ${row.negativePct}%`}
    >
      <div className="bg-[#16a34a]" style={{ width: `${row.positivePct}%` }} />
      <div className="bg-[#dce1e9]" style={{ width: `${row.neutralPct}%` }} />
      <div className="bg-[#ea5457]" style={{ width: `${row.negativePct}%` }} />
    </div>
  );
}

function BrandCell({ row }: { row: CompetitorViewModel }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-1.5">
        <span className="truncate text-sm font-medium text-[#17233f]">{row.name}</span>
        {row.isOwn && (
          <span className="rounded bg-[#1e51a2]/10 px-1.5 py-0.5 text-[10px] font-medium text-[#1e51a2]">
            本品牌
          </span>
        )}
      </div>
      <div className="mt-0.5 text-[11px] text-[#7b8494]">
        {formatNumber(row.noteCount)} 篇 · {formatNumber(row.totalMentions)} 次提及
      </div>
    </div>
  );
}

function RatioCell({ row }: { row: CompetitorViewModel }) {
  return (
    <div className="min-w-0 space-y-1.5">
      <SentimentBar row={row} />
      <div className="flex justify-between text-[11px] text-[#7b8494]">
        <span className="text-[#148a42]">正面 {row.positivePct.toFixed(1)}%</span>
        <span className="text-[#d13f42]">负面 {row.negativePct.toFixed(1)}%</span>
      </div>
    </div>
  );
}

function NetCell({ row }: { row: CompetitorViewModel }) {
  return (
    <div className="text-right">
      <div
        className={`font-mono text-sm font-semibold ${
          row.netPct >= 0 ? "text-[#148a42]" : "text-[#d13f42]"
        }`}
      >
        {row.netPct >= 0 ? "+" : ""}
        {row.netPct.toFixed(1)}
      </div>
      <div className="text-[11px] text-[#7b8494]">净情绪</div>
    </div>
  );
}

function CompetitorRow({ row }: { row: CompetitorViewModel }) {
  return (
    <li className="grid grid-cols-[104px_1fr_92px] items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-[#f4f6fa]">
      <BrandCell row={row} />
      <RatioCell row={row} />
      <NetCell row={row} />
    </li>
  );
}

function LegendItem({ label, color }: { label: string; color: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-2 w-2 rounded-full ${color}`} aria-hidden="true" />
      {label}
    </span>
  );
}

function SentimentLegend() {
  return (
    <div className="flex items-center justify-end gap-4 px-1 text-[11px] text-[#7b8494]">
      <LegendItem label="正面" color="bg-[#16a34a]" />
      <LegendItem label="中性" color="bg-[#dce1e9]" />
      <LegendItem label="负面" color="bg-[#ea5457]" />
    </div>
  );
}

function RowHeader() {
  return (
    <div className="flex items-center justify-between px-1 text-[11px] text-[#7b8494]">
      <span>机构</span>
      <span>正面 / 中性 / 负面</span>
      <span>净情绪</span>
    </div>
  );
}

export function CompetitorBar({ data }: CompetitorBarProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-[#7b8494]">
        暂无竞品数据
      </div>
    );
  }

  const rows = toRows(data);

  return (
    <div className="space-y-3">
      <SentimentLegend />
      <RowHeader />
      <ol className="space-y-1" aria-label="竞品情绪对比排行">
        {rows.map((row) => (
          <CompetitorRow key={row.name} row={row} />
        ))}
      </ol>
    </div>
  );
}
