"use client";

import { Heart, MessageCircle } from "lucide-react";
import type { HotTopic } from "@/types";
import { SENTIMENT_CONFIG, formatNumber } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

interface HotTopicsProps {
  topics: HotTopic[];
  loading: boolean;
}

export function HotTopics({ topics, loading }: HotTopicsProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-9 w-full" />
        ))}
      </div>
    );
  }

  if (topics.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-[#7b8494] text-sm">
        暂无热门话题
      </div>
    );
  }

  const maxLikes = Math.max(...topics.map((t) => t.likes), 1);

  return (
    <ol className="space-y-1.5" aria-label="热门笔记排行">
      {topics.map((topic, i) => {
        const sentiment = topic.sentiment?.label;
        const cfg = sentiment
          ? (SENTIMENT_CONFIG[sentiment] ?? SENTIMENT_CONFIG.neutral)
          : SENTIMENT_CONFIG.neutral;
        const pct = (topic.likes / maxLikes) * 100;

        return (
          <li key={topic.note_id} className="flex items-center gap-2.5">
            <span className="w-5 shrink-0 text-right font-mono text-xs text-[#7b8494]">
              {i + 1}
            </span>
            <div className="relative min-w-0 flex-1 overflow-hidden rounded">
              <div
                className="absolute inset-y-0 left-0 rounded transition-all duration-500"
                style={{ width: `${pct}%`, background: cfg.bgColor }}
                aria-hidden="true"
              />
              <div className="relative flex items-center justify-between gap-2 px-2 py-1.5">
                <span className="truncate text-xs text-[#1f2a44]">
                  {topic.title || "(无标题)"}
                </span>
                <div className="flex shrink-0 items-center gap-2 text-xs text-[#7b8494]">
                  <span className="flex items-center gap-0.5">
                    <Heart size={9} aria-hidden="true" />
                    <span className="font-mono">{formatNumber(topic.likes)}</span>
                  </span>
                  <span className="flex items-center gap-0.5">
                    <MessageCircle size={9} aria-hidden="true" />
                    <span className="font-mono">{formatNumber(topic.comments)}</span>
                  </span>
                  {sentiment && (
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ background: cfg.color }}
                      aria-label={cfg.label}
                    />
                  )}
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
