import { apiPost } from "@/lib/api/http";
import type { EvaluationReport } from "@/types/api";

export type EvaluationRequest = {
  subscriber_count: number;
  seed: number;
  intervention_budget: number | null;
  bootstrap_samples: number;
  include_oracle: boolean;
};

export function runEvaluation(body: EvaluationRequest) {
  return apiPost<EvaluationReport>("/api/evaluation/run", body);
}
