import { apiGet } from "@/lib/api/http";
import { scopedQuery } from "@/lib/run";
import type { DashboardSummary } from "@/types/api";

export function getDashboardSummary(runId: string) {
  return apiGet<DashboardSummary>(`/api/dashboard/summary?${scopedQuery(runId)}`);
}
