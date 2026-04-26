"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, FileText, Sparkles } from "lucide-react";
import type { WsMessage, Note } from "@/types";
import { useWebSocket, type ConnectionStatus } from "@/lib/websocket";
import { SentimentBadge } from "@/components/ui/badge";
import { formatRelative } from "@/lib/utils";

interface FeedItem {
  id: string;
  type: WsMessage["type"];
  note?: Note;
  message?: string;
  timestamp: string;
}

interface RealtimeFeedProps {
  onStatusChange?: (status: ConnectionStatus) => void;
}

const MAX_ITEMS = 20;

export function RealtimeFeed({ onStatusChange }: RealtimeFeedProps) {
  const [items, setItems] = useState<FeedItem[]>([]);

  const handleMessage = useCallback((msg: WsMessage) => {
    const item: FeedItem = {
      id: `${msg.type}-${Date.now()}-${Math.random()}`,
      type: msg.type,
      timestamp: msg.timestamp ?? new Date().toISOString(),
    };

    if (msg.type === "new_note") item.note = msg.data as Note;
    if (msg.type === "alert") {
      item.message = (msg.data as { message: string }).message;
    }

    setItems((prev) => [item, ...prev].slice(0, MAX_ITEMS));
  }, []);

  const status = useWebSocket(handleMessage);

  useEffect(() => {
    onStatusChange?.(status);
  }, [status, onStatusChange]);

  return (
    <div className="space-y-2" aria-live="polite" aria-label="实时动态">
      {items.length === 0 && (
        <p className="py-6 text-center text-xs text-[#71717a]">等待实时数据…</p>
      )}
      {items.map((item) => (
        <FeedCard key={item.id} item={item} />
      ))}
    </div>
  );
}

function FeedCard({ item }: { item: FeedItem }) {
  if (item.type === "alert") {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-[#f59e0b]/20 bg-[#f59e0b]/5 p-3 animate-fade-in">
        <AlertTriangle size={13} className="mt-0.5 shrink-0 text-[#f59e0b]" />
        <div>
          <p className="text-xs font-medium text-[#f4f4f5]">舆情预警</p>
          <p className="text-xs text-[#a1a1aa]">{item.message}</p>
        </div>
      </div>
    );
  }

  if (item.type === "sentiment_update") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-[#1c1c1f] bg-[#111113] p-3 animate-fade-in">
        <Sparkles size={13} className="shrink-0 text-[#1e51a2]" />
        <span className="text-xs text-[#71717a]">情感分析完成</span>
        <span className="ml-auto text-xs text-[#71717a]">
          {formatRelative(item.timestamp)}
        </span>
      </div>
    );
  }

  if (item.note) {
    return (
      <div className="rounded-lg border border-[#1c1c1f] bg-[#111113] p-3 animate-fade-in">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-start gap-2">
            <FileText size={13} className="mt-0.5 shrink-0 text-[#1e51a2]" />
            <p className="truncate text-xs text-[#f4f4f5]">
              {item.note.title || item.note.content.slice(0, 40)}
            </p>
          </div>
          {item.note.sentiment && (
            <SentimentBadge label={item.note.sentiment.label} />
          )}
        </div>
        <div className="mt-1.5 flex items-center gap-2 pl-5">
          <span className="text-xs text-[#71717a]">{item.note.author.nickname}</span>
          <span className="ml-auto text-xs text-[#71717a]">
            {formatRelative(item.timestamp)}
          </span>
        </div>
      </div>
    );
  }

  return null;
}
