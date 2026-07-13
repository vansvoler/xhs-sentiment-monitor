"use client";

import { Heart, MessageCircle, Share2, Bookmark, ExternalLink } from "lucide-react";
import type { Note } from "@/types";
import { formatRelative, formatNumber, noteUrl } from "@/lib/utils";
import { SentimentBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface NotesTableProps {
  notes: Note[];
  loading: boolean;
  keywords?: string[];
  selectedKw: string;
  onSelectKw: (kw: string) => void;
}

export function NotesTable({
  notes,
  loading,
  keywords = [],
  selectedKw,
  onSelectKw,
}: NotesTableProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-[#eaeef4] bg-[#ffffff] p-4 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* 关键词筛选 */}
      {keywords.length > 0 && (
        <select
          value={selectedKw}
          onChange={(e) => onSelectKw(e.target.value)}
          className="w-full rounded-lg border border-[#dce1e9] bg-[#eef2f8] px-3 py-1.5 text-xs text-[#5a6474] outline-none focus:border-[#1e51a2] transition-colors cursor-pointer"
          aria-label="按关键词过滤"
        >
          <option value="">全部关键词</option>
          {keywords.map((kw) => (
            <option key={kw} value={kw}>{kw}</option>
          ))}
        </select>
      )}

      {notes.length === 0 && (
        <div className="flex h-32 items-center justify-center text-[#7b8494] text-sm">
          {selectedKw ? `无「${selectedKw}」相关笔记` : "暂无笔记数据"}
        </div>
      )}

      {/* 固定高度滚动区，避免长列表把整页无限拉长 */}
      <div className="max-h-[620px] space-y-2 overflow-y-auto pr-1">
        {notes.map((note) => (
          <article
            key={note.note_id}
            className="rounded-lg border border-[#eaeef4] bg-[#ffffff] p-4 transition-colors hover:border-[#eef2f8] hover:bg-[#eef2f8] animate-fade-in"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-[#1f2a44]">
                  {note.title || "(无标题)"}
                </p>
                <p className="mt-0.5 line-clamp-2 text-xs text-[#5a6474]">
                  {note.content}
                </p>
              </div>
              {note.sentiment && (
                <SentimentBadge label={note.sentiment.label} score={note.sentiment.score} />
              )}
            </div>

            <div className="mt-3 flex items-center gap-4 text-xs text-[#7b8494]">
              <span>{note.author.nickname}</span>
              <div className="flex items-center gap-1">
                <Heart size={11} aria-hidden="true" />
                <span className="font-mono">{formatNumber(note.stats.likes)}</span>
              </div>
              <div className="flex items-center gap-1">
                <MessageCircle size={11} aria-hidden="true" />
                <span className="font-mono">{formatNumber(note.stats.comments)}</span>
              </div>
              <div className="flex items-center gap-1">
                <Share2 size={11} aria-hidden="true" />
                <span className="font-mono">{formatNumber(note.stats.shares)}</span>
              </div>
              <div className="flex items-center gap-1">
                <Bookmark size={11} aria-hidden="true" />
                <span className="font-mono">{formatNumber(note.stats.collects)}</span>
              </div>
              <span className="ml-auto">发布于 {formatRelative(note.published_at)}</span>
              <a
                href={noteUrl(note.note_id, note.xsec_token)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[#1e51a2] transition-colors hover:underline"
                aria-label="打开小红书原文"
              >
                <ExternalLink size={11} aria-hidden="true" />
                原文
              </a>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
