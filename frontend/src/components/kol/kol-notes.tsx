"use client";

import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";

import type { KolNote, SentimentLabel } from "@/types";
import { fetchKolNotes } from "@/lib/api";
import { TagBadge } from "@/components/ui/badge";
import { formatNumber, formatRelative, noteUrl, SENTIMENT_CONFIG } from "@/lib/utils";

/**
 * 候选作者名下命中监控词的笔记——综合分的原始依据。
 * 分数只说明"离品牌多近、互动多高"，看不出内容质感；决定要不要聊这个人，
 * 靠的是他到底写了什么。
 */
export function KolNotes({ userId }: { userId: string }) {
  const [notes, setNotes] = useState<KolNote[] | null>(null);

  useEffect(() => {
    let alive = true;
    fetchKolNotes(userId)
      .then((n) => alive && setNotes(n))
      .catch(() => alive && setNotes([]));
    return () => {
      alive = false;
    };
  }, [userId]);

  if (notes === null) {
    return <div className="h-16 animate-pulse rounded bg-[#eaeef4]" />;
  }
  if (notes.length === 0) {
    return <p className="py-3 text-[12px] text-[#7b8494]">没有命中当前监控词的笔记</p>;
  }

  return (
    <ul className="space-y-1.5">
      {notes.map((n) => (
        <KolNoteItem key={n.note_id} note={n} />
      ))}
    </ul>
  );
}

function KolNoteItem({ note }: { note: KolNote }) {
  const sent = note.sentiment
    ? SENTIMENT_CONFIG[note.sentiment as SentimentLabel]
    : undefined;
  return (
    <li className="flex items-center gap-3 rounded border border-[#eef2f8] bg-white px-3 py-2">
      <TagBadge>{note.search_keyword}</TagBadge>
      <a
        href={noteUrl(note.note_id, note.xsec_token)}
        target="_blank"
        rel="noreferrer"
        className="flex flex-1 items-center gap-1 truncate text-[#1f2a44] hover:text-[#1e51a2] hover:underline"
      >
        <span className="truncate">{note.title || "（无标题）"}</span>
        <ExternalLink size={11} className="shrink-0 text-[#7b8494]" />
      </a>
      {sent && (
        <span
          className="shrink-0 rounded px-1.5 py-0.5 text-[12px]"
          style={{ background: sent.bgColor, color: sent.textColor }}
        >
          {sent.label}
        </span>
      )}
      <span className="shrink-0 text-[12px] text-[#7b8494]">
        赞 {formatNumber(note.likes)} · 评 {formatNumber(note.comments)} · 藏{" "}
        {formatNumber(note.collects)}
      </span>
      {note.published_at && (
        <span className="w-20 shrink-0 text-right text-[12px] text-[#7b8494]">
          {formatRelative(note.published_at)}
        </span>
      )}
    </li>
  );
}
