"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { CompetitorData } from "@/types";

interface CompetitorBarProps {
  data: CompetitorData[];
}

export function CompetitorBar({ data }: CompetitorBarProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-[#71717a] text-sm">
        暂无竞品数据
      </div>
    );
  }

  const formatted = data.map((d) => ({
    name: d.name,
    正面率: +(d.positive_rate * 100).toFixed(1),
    负面率: +(d.negative_rate * 100).toFixed(1),
    提及数: d.total_mentions,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={formatted} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1c1c1f" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: "#71717a", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#71717a", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          unit="%"
        />
        <Tooltip
          contentStyle={{
            background: "#18181b",
            border: "1px solid #27272a",
            borderRadius: "8px",
            fontSize: "12px",
            color: "#f4f4f5",
          }}
        />
        <Bar dataKey="正面率" fill="#22c55e" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {formatted.map((_, i) => (
            <Cell key={i} fill="#22c55e" fillOpacity={0.85} />
          ))}
        </Bar>
        <Bar dataKey="负面率" fill="#f87171" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {formatted.map((_, i) => (
            <Cell key={i} fill="#f87171" fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
