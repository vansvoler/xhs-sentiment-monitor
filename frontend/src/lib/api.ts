import type {
  Note,
  Comment,
  NotesSummary,
  SentimentStats,
  TrendDataPoint,
  CompetitorData,
  HotTopic,
  KeywordConfig,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

// ── 笔记 ─────────────────────────────────────────────────────────────────────

export function fetchNotes(skip = 0, limit = 20, category?: string, sentiment?: string): Promise<Note[]> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (category) params.set("category", category);
  if (sentiment) params.set("sentiment", sentiment);
  return get<Note[]>(`/api/notes?${params}`);
}

export function fetchNotesSummary(category?: string): Promise<NotesSummary> {
  const params = category ? `?category=${category}` : "";
  return get<NotesSummary>(`/api/notes/stats/summary${params}`);
}

// ── 评论 ─────────────────────────────────────────────────────────────────────

export function fetchNoteComments(noteId: string, limit = 30): Promise<Comment[]> {
  return get<Comment[]>(`/api/comments/note/${noteId}?limit=${limit}`);
}

// ── 情感 ─────────────────────────────────────────────────────────────────────

export function fetchSentimentStats(): Promise<SentimentStats> {
  return get<SentimentStats>("/api/sentiment/stats");
}

// ── 趋势 ─────────────────────────────────────────────────────────────────────

export function fetchTrendSeries(days = 7): Promise<TrendDataPoint[]> {
  return get<TrendDataPoint[]>(`/api/trends/series?days=${days}`);
}

export function fetchHotTopics(limit = 10, hours = 24): Promise<HotTopic[]> {
  return get<HotTopic[]>(`/api/trends/hot-topics?limit=${limit}&hours=${hours}`);
}

// ── 竞品 ─────────────────────────────────────────────────────────────────────

export function fetchCompetitors(days = 30): Promise<CompetitorData[]> {
  return get<CompetitorData[]>(`/api/competitors/compare?days=${days}`);
}

// ── 配置 ─────────────────────────────────────────────────────────────────────

export function fetchKeywords(): Promise<KeywordConfig> {
  return get<KeywordConfig>("/api/config/keywords");
}
