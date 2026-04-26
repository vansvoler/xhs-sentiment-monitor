"use client";

import { useState, useCallback } from "react";
import { Heart, MessageCircle, Share2, Bookmark, ChevronDown, ChevronUp, ThumbsUp } from "lucide-react";
import type { Note, Comment } from "@/types";
import { formatRelative, formatNumber } from "@/lib/utils";
import { SentimentBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchNoteComments } from "@/lib/api";

interface NotesTableProps {
  notes: Note[];
  loading: boolean;
  keywords?: string[];
}

// 评论列表（懒加载）
function CommentPanel({ noteId }: { noteId: string }) {
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    if (comments !== null || fetching) return;
    setFetching(true);
    try {
      const data = await fetchNoteComments(noteId);
      setComments(data);
    } catch {
      setError(true);
    } finally {
      setFetching(false);
    }
  }, [noteId, comments, fetching]);

  // 首次渲染就触发加载
  if (comments === null && !fetching && !error) {
    load();
  }

  if (fetching) {
    return (
      <div className="space-y-2 pt-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex gap-2">
            <Skeleton className="h-3 w-12 shrink-0" />
            <Skeleton className="h-3 flex-1" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="pt-3 text-xs text-[#71717a]">评论加载失败</p>;
  }

  if (!comments || comments.length === 0) {
    return <p className="pt-3 text-xs text-[#71717a]">暂无评论数据</p>;
  }

  return (
    <ul className="mt-3 space-y-2 border-t border-[#1c1c1f] pt-3">
      {comments.map((c) => (
        <li key={c.comment_id} className="flex items-start gap-2 text-xs">
          <span className="shrink-0 font-medium text-[#71717a] w-20 truncate">
            {c.author.nickname}
          </span>
          <span className="flex-1 text-[#a1a1aa] leading-relaxed">{c.content}</span>
          <div className="flex items-center gap-2 shrink-0">
            {c.likes > 0 && (
              <span className="flex items-center gap-0.5 text-[#52525b]">
                <ThumbsUp size={10} aria-hidden="true" />
                <span className="font-mono">{formatNumber(c.likes)}</span>
              </span>
            )}
            {c.sentiment ? (
              <SentimentBadge label={c.sentiment.label} score={c.sentiment.score} />
            ) : (
              <span className="text-[#3f3f46] italic">待分析</span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function NotesTable({ notes, loading, keywords = [] }: NotesTableProps) {
  const [selectedKw, setSelectedKw] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = selectedKw
    ? notes.filter((n) => n.keywords?.includes(selectedKw))
    : notes;

  const toggle = (noteId: string) =>
    setExpandedId((prev) => (prev === noteId ? null : noteId));

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-[#1c1c1f] bg-[#111113] p-4 space-y-2">
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
          onChange={(e) => setSelectedKw(e.target.value)}
          className="w-full rounded-lg border border-[#27272a] bg-[#18181b] px-3 py-1.5 text-xs text-[#a1a1aa] outline-none focus:border-[#1e51a2] transition-colors cursor-pointer"
          aria-label="按关键词过滤"
        >
          <option value="">全部关键词</option>
          {keywords.map((kw) => (
            <option key={kw} value={kw}>{kw}</option>
          ))}
        </select>
      )}

      {filtered.length === 0 && (
        <div className="flex h-32 items-center justify-center text-[#71717a] text-sm">
          {selectedKw ? `无「${selectedKw}」相关笔记` : "暂无笔记数据"}
        </div>
      )}

      <div className="space-y-2">
        {filtered.map((note) => {
          const expanded = expandedId === note.note_id;
          return (
            <article
              key={note.note_id}
              className="rounded-lg border border-[#1c1c1f] bg-[#111113] p-4 transition-colors hover:border-[#2a2a2a] hover:bg-[#18181b] animate-fade-in"
            >
              {/* 标题行 — 点击展开/收起 */}
              <button
                className="w-full text-left"
                onClick={() => toggle(note.note_id)}
                aria-expanded={expanded}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-[#f4f4f5]">
                      {note.title || "(无标题)"}
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-[#a1a1aa]">
                      {note.content}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {note.sentiment && (
                      <SentimentBadge label={note.sentiment.label} score={note.sentiment.score} />
                    )}
                    {note.stats.comments > 0 && (
                      expanded
                        ? <ChevronUp size={14} className="text-[#52525b]" aria-hidden="true" />
                        : <ChevronDown size={14} className="text-[#52525b]" aria-hidden="true" />
                    )}
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-4 text-xs text-[#71717a]">
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
                  <span className="ml-auto">{formatRelative(note.collected_at)}</span>
                </div>
              </button>

              {/* 评论展开区 */}
              {expanded && <CommentPanel noteId={note.note_id} />}
            </article>
          );
        })}
      </div>
    </div>
  );
}
