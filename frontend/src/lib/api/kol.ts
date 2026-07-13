// KOL 挖掘接口
import type { AccountType, KolCandidate, KolNote, KolStatus } from "@/types";

import { BASE, get, post } from "./client";

export interface KolFilters {
  keyword?: string;
  minEngagement?: number;
  accountType?: AccountType;
  status?: KolStatus;
  limit?: number;
}

export function fetchKolCandidates(f: KolFilters = {}): Promise<KolCandidate[]> {
  const params = new URLSearchParams();
  if (f.keyword) params.set("keyword", f.keyword);
  if (f.minEngagement) params.set("min_engagement", String(f.minEngagement));
  if (f.accountType) params.set("account_type", f.accountType);
  if (f.status) params.set("status", f.status);
  params.set("limit", String(f.limit ?? 100));
  return get<KolCandidate[]>(`/api/kol/candidates?${params}`);
}

/** 该候选命中监控词的笔记，新的在前 */
export function fetchKolNotes(userId: string): Promise<KolNote[]> {
  return get<KolNote[]>(`/api/kol/${userId}/notes`);
}

export function setKolStatus(
  userId: string,
  status: KolStatus,
  remark?: string,
): Promise<{ status: string }> {
  return post(`/api/kol/${userId}/status`, { status, remark });
}

/** 人工校正账号分类；传空串撤销校正，交还昵称规则 */
export function setKolAccountType(
  userId: string,
  accountType: AccountType | "",
): Promise<{ account_type: string }> {
  return post(`/api/kol/${userId}/account-type`, { account_type: accountType });
}

export function enrichKol(
  userId: string,
): Promise<{ cached: boolean; profile: Record<string, unknown> }> {
  return post<{ cached: boolean; profile: Record<string, unknown> }>(
    `/api/kol/${userId}/enrich`,
  );
}

export const kolExportUrl = `${BASE}/api/kol/export`;
