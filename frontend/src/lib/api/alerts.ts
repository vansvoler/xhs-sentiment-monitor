// 舆情预警接口
import type { Alert, AlertLevel, AlertStatus } from "@/types";

import { get, post } from "./client";

export function fetchAlerts(
  opts: { status?: AlertStatus; level?: AlertLevel; limit?: number } = {},
): Promise<Alert[]> {
  const params = new URLSearchParams();
  if (opts.status) params.set("status", opts.status);
  if (opts.level) params.set("level", opts.level);
  params.set("limit", String(opts.limit ?? 50));
  return get<Alert[]>(`/api/alerts/?${params}`);
}

export function acknowledgeAlert(alertId: string): Promise<{ status: string }> {
  return post<{ status: string }>(`/api/alerts/${alertId}/ack`);
}
