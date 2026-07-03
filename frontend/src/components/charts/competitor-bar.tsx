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
      <div className="flex h-48 items-center justify-center text-[#7b8494] text-sm">
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
        <CartesianGrid strokeDasharray="3 3" stroke="#eaeef4" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: "#7b8494", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#7b8494", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          unit="%"
        />
        <Tooltip
          contentStyle={{
            background: "#eef2f8",
            border: "1px solid #dce1e9",
            borderRadius: "8px",
            fontSize: "12px",
            color: "#1f2a44",
          }}
        />
        <Bar dataKey="正面率" fill="#16a34a" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {formatted.map((_, i) => (
            <Cell key={i} fill="#16a34a" fillOpacity={0.85} />
          ))}
        </Bar>
        <Bar dataKey="负面率" fill="#ea5457" radius={[4, 4, 0, 0]} maxBarSize={40}>
          {formatted.map((_, i) => (
            <Cell key={i} fill="#ea5457" fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
