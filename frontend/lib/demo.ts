export const DEMO_CONFIG = {
  subscriber_count: 100,
  halt_rate: 0.45,
  reactivation_rate: 0.65,
  domestic_card_ratio: 0.75,
  risk_flag_rate: 0.08,
  dispute_rate: 0.03,
  opt_out_rate: 0.04,
  plan_amount_min_paise: 49900,
  plan_amount_max_paise: 1999900,
  min_missed_cycles: 1,
  max_missed_cycles: 6,
  intervention_budget: 25,
  seed: 42,
} as const;

export const DEMO_STRATEGIES = ["naive", "rule_based"] as const;
