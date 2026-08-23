import { apiGet } from "@/lib/api/http";
import type { SimulationRun } from "@/types/api";

export function listRuns() {
  return apiGet<SimulationRun[]>("/api/runs");
}

export function getRun(runId: string) {
  return apiGet<SimulationRun>(`/api/runs/${encodeURIComponent(runId)}`);
}
