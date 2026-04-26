import { format, formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import type { SentimentLabel } from "@/types";

export function formatDate(iso: string): string {
  return format(new Date(iso), "MM-dd HH:mm");
}

export function formatRelative(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: zhCN });
}

export function formatNumber(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}w`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

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
