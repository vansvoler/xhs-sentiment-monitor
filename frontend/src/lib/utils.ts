import { format, formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import type { SentimentLabel } from "@/types";

// 后端时间是无时区后缀的 UTC（FastAPI 序列化 naive datetime），
// 直接 new Date() 会被当成本地时间导致 +8h 偏移，必须补 Z 再解析
export function parseUtc(iso: string): Date {
  const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(iso);
  return new Date(hasTz ? iso : `${iso}Z`);
}

export function formatDate(iso: string): string {
  return format(parseUtc(iso), "MM-dd HH:mm");
}

export function formatRelative(iso: string): string {
  return formatDistanceToNow(parseUtc(iso), { addSuffix: true, locale: zhCN });
}

export function noteUrl(noteId: string, xsecToken?: string | null): string {
  const base = `https://www.xiaohongshu.com/explore/${noteId}`;
  return xsecToken ? `${base}?xsec_token=${xsecToken}&xsec_source=pc_search` : base;
}

export function userUrl(userId: string): string {
  return `https://www.xiaohongshu.com/user/profile/${userId}`;
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
