// 小红书核心接口：笔记 / 情感 / 趋势 / 竞品 / 配置
import type {
  CompetitorData,
  HotTopic,
  KeywordConfig,
  Note,
  NotesSummary,
  TrendDataPoint,
} from "@/types";

import { BASE, get } from "./client";

export function fetchNotes(
  skip = 0, limit = 20, category?: string, sentiment?: string, keyword?: string,
): Promise<Note[]> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (category) params.set("category", category);
  if (sentiment) params.set("sentiment", sentiment);
  if (keyword) params.set("keyword", keyword);
  return get<Note[]>(`/api/notes/?${params}`);
}

export function fetchNotesSummary(category?: string): Promise<NotesSummary> {
  const params = category ? `?category=${category}` : "";
  return get<NotesSummary>(`/api/notes/stats/summary${params}`);
}

export function fetchTrendSeries(days = 7, category?: string): Promise<TrendDataPoint[]> {
  const params = new URLSearchParams({ days: String(days) });
  if (category) params.set("category", category);
  return get<TrendDataPoint[]>(`/api/trends/series?${params}`);
}

export function fetchHotTopics(
  limit = 10, hours = 24, category?: string,
): Promise<HotTopic[]> {
  const params = new URLSearchParams({ limit: String(limit), hours: String(hours) });
  if (category) params.set("category", category);
  return get<HotTopic[]>(`/api/trends/hot-topics?${params}`);
}

export function fetchCompetitors(days = 30): Promise<CompetitorData[]> {
  return get<CompetitorData[]>(`/api/competitors/compare?days=${days}`);
}

export function fetchKeywords(): Promise<KeywordConfig> {
  return get<KeywordConfig>("/api/config/keywords");
}

export function addKeyword(keyword: string, category: string): Promise<KeywordConfig> {
  return fetch(`${BASE}/api/config/keywords`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword, category }),
  }).then((r) => {
    if (!r.ok) throw new Error(`add keyword → ${r.status}`);
    return r.json();
  });
}

export function removeKeyword(keyword: string): Promise<KeywordConfig> {
  return fetch(`${BASE}/api/config/keywords/${encodeURIComponent(keyword)}`, {
    method: "DELETE",
  }).then((r) => {
    if (!r.ok) throw new Error(`remove keyword → ${r.status}`);
    return r.json();
  });
}
