"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, FileText, Sparkles } from "lucide-react";
import type { WsMessage, Note } from "@/types";
import { fetchNotes } from "@/lib/api";
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
const SEED_COUNT = 10;

// 刷新页面后 WebSocket 流从零开始，先用最近入库的笔记垫底，避免长时间空面板
function seedItems(notes: Note[]): FeedItem[] {
  return notes.map((note) => ({
    id: `seed-${note.note_id}`,
    type: "new_note",
    note,
    timestamp: note.collected_at,
  }));
}

export function RealtimeFeed({ onStatusChange }: RealtimeFeedProps) {
  const [items, setItems] = useState<FeedItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchNotes(0, SEED_COUNT)
      .then((notes) => {
        if (cancelled) return;
        // 实时推送可能先到，垫底数据只补在已有条目之后
        setItems((prev) => [...prev, ...seedItems(notes)].slice(0, MAX_ITEMS));
      })
      .catch(() => {}); // 垫底失败不影响实时流
    return () => {
      cancelled = true;
    };
  }, []);

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
        <p className="py-6 text-center text-xs text-[#7b8494]">等待实时数据…</p>
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
      <div className="flex items-start gap-2 rounded-lg border border-[#e08a1e]/20 bg-[#e08a1e]/5 p-3 animate-fade-in">
        <AlertTriangle size={13} className="mt-0.5 shrink-0 text-[#e08a1e]" />
        <div>
          <p className="text-xs font-medium text-[#1f2a44]">舆情预警</p>
          <p className="text-xs text-[#5a6474]">{item.message}</p>
        </div>
      </div>
    );
  }

  if (item.type === "sentiment_update") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-[#eaeef4] bg-[#ffffff] p-3 animate-fade-in">
        <Sparkles size={13} className="shrink-0 text-[#1e51a2]" />
        <span className="text-xs text-[#7b8494]">情感分析完成</span>
        <span className="ml-auto text-xs text-[#7b8494]">
          {formatRelative(item.timestamp)}
        </span>
      </div>
    );
  }

  if (item.note) {
    return (
      <div className="rounded-lg border border-[#eaeef4] bg-[#ffffff] p-3 animate-fade-in">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-start gap-2">
            <FileText size={13} className="mt-0.5 shrink-0 text-[#1e51a2]" />
            <p className="truncate text-xs text-[#1f2a44]">
              {item.note.title || item.note.content.slice(0, 40)}
            </p>
          </div>
          {item.note.sentiment && (
            <SentimentBadge label={item.note.sentiment.label} />
          )}
        </div>
        <div className="mt-1.5 flex items-center gap-2 pl-5">
          <span className="text-xs text-[#7b8494]">{item.note.author.nickname}</span>
          <span className="ml-auto text-xs text-[#7b8494]">
            {formatRelative(item.timestamp)}
          </span>
        </div>
      </div>
    );
  }

  return null;
}
