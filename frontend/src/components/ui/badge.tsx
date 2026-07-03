import type { SentimentLabel } from "@/types";
import { SENTIMENT_CONFIG } from "@/lib/utils";

interface SentimentBadgeProps {
  label: SentimentLabel;
  score?: number;
}

export function SentimentBadge({ label, score }: SentimentBadgeProps) {
  const cfg = SENTIMENT_CONFIG[label];
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ background: cfg.bgColor, color: cfg.textColor }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: cfg.color }}
        aria-hidden="true"
      />
      {cfg.label}
      {score !== undefined && (
        <span className="opacity-60 font-mono">{(score * 100).toFixed(0)}%</span>
      )}
    </span>
  );
}

interface TagBadgeProps {
  children: React.ReactNode;
}

export function TagBadge({ children }: TagBadgeProps) {
  return (
    <span className="inline-flex items-center rounded px-1.5 py-0.5 text-xs bg-[#eef2f8] text-[#5a6474] border border-[#dce1e9]">
      {children}
    </span>
  );
}
