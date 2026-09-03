import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AgentWorkbench } from "@/components/cases/AgentWorkbench";
import type { RecoveryCaseDetail } from "@/types/api";

const detail: RecoveryCaseDetail = {
  case: {
    case_id: "case_1",
    run_id: "run_1",
    subscription_id: "sub_1",
    customer_id: "cust_1",
    synthetic_case_key: null,
    synthetic_customer_key: null,
    halt_episode_id: "he_1",
    status: "open",
    invoice_ids: ["inv_1"],
    invoice_count: 1,
    backlog_amount_paise: 499900,
    oldest_invoice_at: null,
    newest_invoice_at: null,
    halted_at: "2026-01-01T00:00:00Z",
    reactivated_at: "2026-02-01T00:00:00Z",
    halt_duration_days: 31,
    card_type: "international",
    risk_flags: [],
    historical_payment_success_rate: 0.7,
    previous_failure_count: 0,
    previous_halt_count: 1,
    subscription_age_days: 90,
    customer_opted_out: false,
    has_active_dispute: false,
    policy_version: "v1",
    attempt_count: 0,
    last_contact_at: null,
    amount_recovered_paise: 0,
    created_at: "2026-02-01T00:00:00Z",
    updated_at: "2026-02-01T00:00:00Z",
    customer_name: "Ada",
    policy_status: "eligible",
    allowed_actions: ["send_payment_link"],
    blocked_actions: [],
    requires_escalation: false,
    stop: false,
    model_analysis: {
      p_no_action: 0.31,
      selected_action: "send_payment_link",
      p_selected_action: 0.67,
      estimated_uplift: 0.36,
      expected_incremental_recovery_paise: 539000,
      estimated_recovery_no_action_paise: 464800,
      estimated_recovery_selected_paise: 1004800,
      model_version: "m5-v1",
      model_type: "logistic_regression",
      candidates: [],
      synthetic: true,
    },
  },
  invoices: [],
  policy: {
    policy_version: "v1",
    allowed_actions: ["send_payment_link", "no_action"],
    blocked_actions: ["attempt_manual_charge"],
    reason_codes: [],
    requires_escalation: false,
    stop: false,
    applied_rules: [],
  },
  customer_name: "Ada",
  subscription_status: "active",
  subscription_created_at: "2025-01-01T00:00:00Z",
  halt_episodes: [],
};

describe("AgentWorkbench", () => {
  it("labels simulated execution and does not auto-call Claude", () => {
    const html = renderToStaticMarkup(<AgentWorkbench detail={detail} />);
    expect(html).toContain("SIMULATED EXECUTION — NO REAL PAYMENT WILL BE ATTEMPTED");
    expect(html).toContain("Run simulated recovery");
    expect(html).toContain("Generate AI explanation");
    expect(html).toContain("Claude is not");
    expect(html).toContain("Ask AfterDue about this decision");
    expect(html).not.toContain("AI confidence");
  });
});
