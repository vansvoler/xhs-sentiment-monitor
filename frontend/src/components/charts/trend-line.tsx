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
import { parseUtc } from "@/lib/utils";

interface TrendLineProps {
  data: TrendDataPoint[];
}

export function TrendLine({ data }: TrendLineProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-[#7b8494] text-sm">
        暂无趋势数据
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    date: format(parseUtc(d.timestamp), "MM/dd"),
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={formatted} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
        <defs>
          <linearGradient id="gradPositive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#16a34a" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradNegative" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ea5457" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#ea5457" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradNeutral" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#727171" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#727171" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#eaeef4" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: "#7b8494", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#7b8494", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: "#eef2f8",
            border: "1px solid #dce1e9",
            borderRadius: "8px",
            fontSize: "12px",
            color: "#1f2a44",
          }}
          labelStyle={{ color: "#5a6474", marginBottom: 4 }}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value) => (
            <span className="text-xs text-[#5a6474]">
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
          stroke="#16a34a"
          strokeWidth={2}
          fill="url(#gradPositive)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
        <Area
          type="monotone"
          dataKey="negative_count"
          stroke="#ea5457"
          strokeWidth={2}
          fill="url(#gradNegative)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
        <Area
          type="monotone"
          dataKey="neutral_count"
          stroke="#727171"
          strokeWidth={2}
          fill="url(#gradNeutral)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
