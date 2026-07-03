// KOL 挖掘接口
import type { KolCandidate, KolStatus } from "@/types";

import { BASE, get, post } from "./client";

export interface KolFilters {
  keyword?: string;
  minEngagement?: number;
  sentiment?: "positive";
  hideCompetitor?: boolean;
  status?: KolStatus;
  limit?: number;
}

export function fetchKolCandidates(f: KolFilters = {}): Promise<KolCandidate[]> {
  const params = new URLSearchParams();
  if (f.keyword) params.set("keyword", f.keyword);
  if (f.minEngagement) params.set("min_engagement", String(f.minEngagement));
  if (f.sentiment) params.set("sentiment", f.sentiment);
  if (f.hideCompetitor) params.set("hide_competitor", "true");
  if (f.status) params.set("status", f.status);
  params.set("limit", String(f.limit ?? 100));
  return get<KolCandidate[]>(`/api/kol/candidates?${params}`);
}

export function setKolStatus(
  userId: string,
  status: KolStatus,
  remark?: string,
): Promise<{ status: string }> {
  return fetch(`${BASE}/api/kol/${userId}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, remark }),
  }).then((r) => {
    if (!r.ok) throw new Error(`status → ${r.status}`);
    return r.json();
  });
}

export function enrichKol(
  userId: string,
): Promise<{ cached: boolean; profile: Record<string, unknown> }> {
  return post<{ cached: boolean; profile: Record<string, unknown> }>(
    `/api/kol/${userId}/enrich`,
  );
}

export const kolExportUrl = `${BASE}/api/kol/export`;
