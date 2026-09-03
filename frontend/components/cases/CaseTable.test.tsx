import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CaseTable } from "@/components/cases/CaseTable";
import type { RecoveryCase } from "@/types/api";

const row: RecoveryCase = {
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
  policy_status: "restricted",
  allowed_actions: ["send_payment_link"],
  blocked_actions: ["attempt_manual_charge"],
  requires_escalation: false,
  stop: false,
};

describe("CaseTable", () => {
  it("uses short aligned headers and keeps money on one line", () => {
    const html = renderToStaticMarkup(<CaseTable cases={[row]} runId="run_1" />);
    expect(html).toContain("Collectible");
    expect(html).toContain("Historical unpaid");
    expect(html).toContain("₹4,999");
    expect(html).toContain("Manual charge blocked");
    expect(html).toContain("whitespace-nowrap");
    expect(html).toContain("View case details");
    expect(html).toContain("case-row-link");
    expect(html).toContain("/cases/case_1");
  });
});
