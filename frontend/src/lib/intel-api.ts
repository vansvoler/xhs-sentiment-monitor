import type {
  IntelOverviewResponse,
  IntelSourceFeedKey,
  IntelSourceResponse,
  SourceNavItem,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export function fetchSourceNav(): Promise<{ items: SourceNavItem[] }> {
  return get("/api/config/source-nav");
}

export function fetchIntelOverview(): Promise<IntelOverviewResponse> {
  return get("/api/intel/overview");
}

export function fetchIntelSource(sourceKey: IntelSourceFeedKey): Promise<IntelSourceResponse> {
  return get(`/api/intel/sources/${sourceKey}`);
}
