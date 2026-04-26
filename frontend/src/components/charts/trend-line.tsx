"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { TrendDataPoint } from "@/types";
import { format } from "date-fns";

interface TrendLineProps {
  data: TrendDataPoint[];
}

export function TrendLine({ data }: TrendLineProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-[#71717a] text-sm">
        暂无趋势数据
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    date: format(new Date(d.timestamp), "MM/dd"),
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={formatted} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
        <defs>
          <linearGradient id="gradPositive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradNegative" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradNeutral" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#52525b" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#52525b" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1c1c1f" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: "#71717a", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#71717a", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "#18181b",
            border: "1px solid #27272a",
            borderRadius: "8px",
            fontSize: "12px",
            color: "#f4f4f5",
          }}
          labelStyle={{ color: "#a1a1aa", marginBottom: 4 }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value) => (
            <span className="text-xs text-[#a1a1aa]">
              {value === "positive_count"
                ? "正面"
                : value === "negative_count"
                  ? "负面"
                  : "中性"}
            </span>
          )}
        />
        <Area
          type="monotone"
          dataKey="positive_count"
          stroke="#22c55e"
          strokeWidth={2}
          fill="url(#gradPositive)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
        <Area
          type="monotone"
          dataKey="negative_count"
          stroke="#f87171"
          strokeWidth={2}
          fill="url(#gradNegative)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
        <Area
          type="monotone"
          dataKey="neutral_count"
          stroke="#52525b"
          strokeWidth={2}
          fill="url(#gradNeutral)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
