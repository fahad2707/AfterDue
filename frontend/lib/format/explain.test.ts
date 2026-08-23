import { describe, expect, it } from "vitest";

import { explainCase } from "@/lib/format/explain";

describe("explainCase", () => {
  it("builds the recovery-window sentence from facts", () => {
    const lines = explainCase({
      invoiceCount: 3,
      backlogPaise: 1499700,
      reasonCodes: ["DOMESTIC_CARD_MANUAL_CHARGE_UNSUPPORTED"],
      allowedActions: ["no_action", "send_payment_link"],
    });
    expect(lines[0]).toContain("3 unpaid invoices");
    expect(lines[0]).toContain("₹14,997");
    expect(lines[1]).toContain("domestic card");
  });
});
