"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { SentimentLabel } from "@/types";
import { SENTIMENT_CONFIG } from "@/lib/utils";

interface SentimentDonutProps {
  distribution: Partial<Record<SentimentLabel, number>>;
}

const LABELS: SentimentLabel[] = ["positive", "negative", "neutral"];

export function SentimentDonut({ distribution }: SentimentDonutProps) {
  const data = LABELS.map((key) => ({
    name: SENTIMENT_CONFIG[key].label,
    value: distribution[key] ?? 0,
    color: SENTIMENT_CONFIG[key].color,
  })).filter((d) => d.value > 0);

  const total = data.reduce((s, d) => s + d.value, 0);

  if (total === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-[#7b8494] text-sm">
        暂无情感数据
      </div>
    );
  }

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={58}
            outerRadius={82}
            paddingAngle={3}
            dataKey="value"
            strokeWidth={0}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "#eef2f8",
              border: "1px solid #dce1e9",
              borderRadius: "8px",
              fontSize: "12px",
              color: "#1f2a44",
            }}
            formatter={(value) => [
              `${String(value)} 条 (${((Number(value) / total) * 100).toFixed(1)}%)`,
            ]}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(value) => (
              <span className="text-xs text-[#5a6474]">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
      {/* 中心总数 */}
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-2xl font-semibold text-[#17233f]">
          {total}
        </span>
        <span className="text-xs text-[#7b8494]">总计</span>
      </div>
    </div>
  );
}
