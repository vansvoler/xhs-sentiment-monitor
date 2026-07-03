import type {
  CreateIntelSourceRequest,
  CreateIntelSourceResponse,
  IntelOverviewResponse,
  IntelSourceFeedKey,
  IntelSourceResponse,
  IntelSourceSyncStatusResponse,
  ProbeIntelSourceRequest,
  ProbeIntelSourceResponse,
  SourceNavItem,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorPayload = await res.json().catch(() => null);
    const detail =
      errorPayload && typeof errorPayload.detail === "string"
        ? errorPayload.detail
        : `API ${path} -> ${res.status}`;
    throw new Error(detail);
  }

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

export function fetchIntelSourceSyncStatus(
  sourceKey: IntelSourceFeedKey,
): Promise<IntelSourceSyncStatusResponse> {
  return get(`/api/intel/sources/${sourceKey}/sync-status`);
}

export function probeIntelSource(
  payload: ProbeIntelSourceRequest,
): Promise<ProbeIntelSourceResponse> {
  return post("/api/intel/sources/probe", payload);
}

export function createIntelSource(
  payload: CreateIntelSourceRequest,
): Promise<CreateIntelSourceResponse> {
  return post("/api/intel/sources", payload);
}
