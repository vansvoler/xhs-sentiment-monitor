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
    color: "#16a34a",
    bgColor: "rgba(22, 163, 74,0.1)",
    textColor: "#16a34a",
  },
  negative: {
    label: "负面",
    color: "#ea5457",
    bgColor: "rgba(234, 84, 87,0.1)",
    textColor: "#ea5457",
  },
  neutral: {
    label: "中性",
    color: "#727171",
    bgColor: "rgba(114, 113, 113,0.15)",
    textColor: "#5a6474",
  },
};
