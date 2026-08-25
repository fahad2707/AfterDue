export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  app_env: string;
  uptime_seconds: number;
};

export type DependencyStatus = {
  ok: boolean;
  detail: string | null;
};

export type ReadyResponse = {
  ready: boolean;
  checks: Record<string, DependencyStatus>;
};

export type MetaResponse = {
  service: string;
  app_env: string;
  policy_version: string;
  llm_enabled: boolean;
  synthetic: boolean;
};

export type SimulationConfig = {
  subscriber_count: number;
  halt_rate: number;
  reactivation_rate: number;
  domestic_card_ratio: number;
  risk_flag_rate: number;
  dispute_rate: number;
  opt_out_rate: number;
  plan_amount_min_paise: number;
  plan_amount_max_paise: number;
  min_missed_cycles: number;
  max_missed_cycles: number;
  intervention_budget: number;
  seed: number;
  contact_cooldown_hours?: number;
  max_attempts?: number;
  suspend_on_halt_rate?: number;
  continue_during_grace_rate?: number;
  grace_cycles?: number;
};

export type WorldSummary = {
  subscriber_count: number;
  always_active_count: number;
  halted_never_returned_count: number;
  reactivated_count: number;
  recovery_case_count: number;
  collectible_recovery_case_count?: number;
  review_required_case_count?: number;
  historical_invoice_count: number;
  historical_unpaid_amount_paise?: number;
  collectible_amount_paise?: number;
  review_required_amount_paise?: number;
  not_collectible_amount_paise?: number;
  revenue_at_risk_paise: number;
  domestic_card_count: number;
  international_card_count: number;
  risk_case_count: number;
  synthetic: boolean;
};

export type StrategyMetrics = {
  strategy_name: string;
  eligible_cases: number;
  intervention_budget: number;
  interventions_used: number;
  revenue_at_risk_paise: number;
  revenue_recovered_paise: number;
  recovery_yield: number;
  recovered_case_count: number;
  failed_intervention_count: number;
  escalation_count: number;
  no_action_count: number;
  revenue_per_intervention_paise: number;
  revenue_per_100_cases_paise: number;
  unnecessary_intervention_count: number;
  incremental_revenue_paise: number;
  action_cost_paise: number;
  synthetic: boolean;
};

export type SimulationRun = {
  run_id: string;
  seed: number;
  synthetic: boolean;
  status: string;
  config: SimulationConfig;
  world_summary: WorldSummary | Record<string, never>;
  strategy_results: Record<string, StrategyMetrics> | Record<string, never>;
  created_at: string;
  completed_at: string | null;
  error: string | null;
};

export type DashboardSummary = {
  run_id: string;
  seed: number;
  synthetic: boolean;
  status: string;
  revenue_at_risk_paise: number;
  historical_unpaid_amount_paise?: number;
  collectible_amount_paise?: number;
  review_required_amount_paise?: number;
  not_collectible_amount_paise?: number;
  collectible_recovery_case_count?: number;
  review_required_case_count?: number;
  recovery_case_count: number;
  reactivated_count: number;
  intervention_budget: number;
  best_baseline_name: string | null;
  best_baseline_recovery_paise: number | null;
  best_baseline_yield: number | null;
  world_summary: WorldSummary | Record<string, unknown>;
  strategy_results: Record<string, StrategyMetrics>;
  config: SimulationConfig | Record<string, unknown>;
  reclaim_vs_best_baseline_paise?: number | null;
};

export type ModelAnalysis = {
  p_no_action: number;
  selected_action: string;
  p_selected_action: number;
  estimated_uplift: number;
  expected_incremental_recovery_paise: number;
  estimated_recovery_no_action_paise: number;
  estimated_recovery_selected_paise: number;
  model_version: string;
  model_type: string;
  candidates: Array<{
    action: string;
    probability: number;
    estimated_uplift: number;
    expected_incremental_recovery_paise: number;
  }>;
  synthetic: boolean;
  feature_contributions?: Array<{ feature: string; coefficient: number }> | null;
};

export type ModelRun = {
  model_run_id: string;
  model_version: string;
  model_type: string;
  dataset_seed: number;
  trained_at: string;
  is_active: boolean;
  feature_schema_hash: string;
  n_examples: number;
  calibrated: boolean;
  selection_reason: string;
  metrics: Record<string, unknown>;
  business_metrics: Record<string, unknown>;
  synthetic: boolean;
};

export type RecoveryCase = {
  case_id: string;
  run_id: string;
  subscription_id: string;
  customer_id: string;
  synthetic_case_key: string | null;
  synthetic_customer_key: string | null;
  halt_episode_id: string;
  status: string;
  collectibility_status?: string;
  invoice_ids: string[];
  invoice_count: number;
  backlog_amount_paise: number;
  historical_unpaid_amount_paise?: number;
  collectible_amount_paise?: number;
  review_required_amount_paise?: number;
  not_collectible_amount_paise?: number;
  collectible_invoice_ids?: string[];
  review_required_invoice_ids?: string[];
  not_collectible_invoice_ids?: string[];
  oldest_invoice_at: string | null;
  newest_invoice_at: string | null;
  halted_at: string;
  reactivated_at: string;
  halt_duration_days: number;
  card_type: string;
  risk_flags: string[];
  historical_payment_success_rate: number;
  previous_failure_count: number;
  previous_halt_count: number;
  subscription_age_days: number;
  customer_opted_out: boolean;
  has_active_dispute: boolean;
  policy_version: string;
  attempt_count: number;
  last_contact_at: string | null;
  amount_recovered_paise: number;
  created_at: string;
  updated_at: string;
  customer_name: string;
  policy_status: string;
  allowed_actions: string[];
  blocked_actions: string[];
  requires_escalation: boolean;
  stop: boolean;
  model_analysis?: ModelAnalysis | null;
};

export type Invoice = {
  invoice_id: string;
  run_id: string;
  subscription_id: string;
  billing_cycle: string;
  period_start: string;
  period_end: string;
  amount_paise: number;
  currency: string;
  status: string;
  halt_episode_id: string | null;
  generated_during_halt: boolean;
  service_delivery_status?: string;
  waived?: boolean;
  merchant_marked_non_collectible?: boolean;
  collectibility_status?: string;
  collectibility_reason_codes?: string[];
  created_at: string;
};

export type AppliedRule = {
  rule_id: string;
  reason_code: string;
  provenance: string;
  source_url: string | null;
  blocked_actions: string[];
  requires_escalation: boolean;
  stop: boolean;
};

export type PolicyDecision = {
  policy_version: string;
  allowed_actions: string[];
  blocked_actions: string[];
  reason_codes: string[];
  requires_escalation: boolean;
  stop: boolean;
  applied_rules: AppliedRule[];
};

export type HaltEpisode = {
  episode_id: string;
  halted_at: string;
  reactivated_at: string | null;
  invoice_ids: string[];
};

export type RecoveryCaseDetail = {
  case: RecoveryCase;
  invoices: Invoice[];
  policy: PolicyDecision;
  customer_name: string;
  subscription_status: string;
  subscription_created_at: string | null;
  halt_episodes: HaltEpisode[];
  model_analysis?: ModelAnalysis | null;
};

export type AuditEntry = {
  audit_id: string;
  run_id: string;
  subscription_id: string;
  seq: number;
  event_type: string;
  actor: string;
  details: Record<string, unknown>;
  ts: string;
};

export type PolicyRule = {
  rule_id: string;
  reason_code: string;
  condition: string;
  effect: string;
  provenance: string;
  source_url: string | null;
};

export type PolicyConfig = {
  policy_version: string;
  max_attempts: number;
  contact_cooldown_hours: number;
  actions: string[];
  rules: PolicyRule[];
  reason_codes: string[];
  provenance_values: string[];
  synthetic: boolean;
};
