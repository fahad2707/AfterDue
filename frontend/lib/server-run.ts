import "server-only";

import { apiGet } from "@/lib/server-api";
import type { SimulationRun } from "@/types/api";

export async function latestRunId(): Promise<string | null> {
  const result = await apiGet<SimulationRun[]>("/api/runs");
  if (!result.ok || result.data.length === 0) return null;
  return result.data[0].run_id;
}

export async function resolveRunId(requested?: string): Promise<string | null> {
  if (requested) return requested;
  return latestRunId();
}
