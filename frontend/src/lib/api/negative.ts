// 负面舆情工作台接口
import type {
  HandleStatus,
  NegativeItem,
  NegativeKind,
  NegativeSort,
  NegativeStatusFilter,
  NegativeSummary,
} from "@/types";

import { get, post } from "./client";

export function fetchNegativeItems(opts: {
  kind: NegativeKind;
  skip?: number;
  limit?: number;
  category?: string;
  keyword?: string;
  status?: NegativeStatusFilter;
  sort?: NegativeSort;
}): Promise<NegativeItem[]> {
  const params = new URLSearchParams({
    kind: opts.kind,
    skip: String(opts.skip ?? 0),
    limit: String(opts.limit ?? 20),
    status: opts.status ?? "open",
    sort: opts.sort ?? "influence",
  });
  if (opts.category) params.set("category", opts.category);
  if (opts.keyword) params.set("keyword", opts.keyword);
  return get<NegativeItem[]>(`/api/sentiment/negative?${params}`);
}

export function fetchNegativeSummary(): Promise<NegativeSummary> {
  return get<NegativeSummary>("/api/sentiment/negative/summary");
}

export function setNegativeStatus(
  kind: NegativeKind,
  id: string,
  status: HandleStatus,
): Promise<{ ok: boolean }> {
  return post<{ ok: boolean }>(
    `/api/sentiment/negative/${kind}/${id}/status`,
    { status },
  );
}
