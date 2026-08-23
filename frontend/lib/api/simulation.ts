import { apiPost } from "@/lib/api/http";
import { DEMO_STRATEGIES } from "@/lib/demo";
import type { SimulationConfig, StrategyMetrics, WorldSummary } from "@/types/api";

export type GenerateResponse = {
  run_id: string;
  world_summary: WorldSummary;
  synthetic: boolean;
};

export type RunStrategiesResponse = {
  run_id: string;
  seed: number;
  strategy_results: Record<string, StrategyMetrics>;
  synthetic: boolean;
};

export function generateWorld(config: SimulationConfig) {
  return apiPost<GenerateResponse>("/api/simulator/generate", config);
}

export function runBaselines(runId: string) {
  return apiPost<RunStrategiesResponse>("/api/simulator/run", {
    run_id: runId,
    strategies: [...DEMO_STRATEGIES],
  });
}
