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