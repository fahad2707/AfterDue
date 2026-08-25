import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BacklogTable } from "@/components/cases/BacklogTable";
import type { Invoice } from "@/types/api";

describe("BacklogTable", () => {
  it("renders halt invoices and a paise total", () => {
    const invoices: Invoice[] = [
      {
        invoice_id: "inv_1",
        run_id: "run_a",
        subscription_id: "sub_1",
        billing_cycle: "2026-02",
        period_start: "2026-02-01T00:00:00Z",
        period_end: "2026-03-01T00:00:00Z",
        amount_paise: 499900,
        currency: "INR",
        status: "issued_unpaid",
        halt_episode_id: "he_1",
        generated_during_halt: true,
        created_at: "2026-02-09T00:00:00Z",
      },
      {
        invoice_id: "inv_2",
        run_id: "run_a",
        subscription_id: "sub_1",
        billing_cycle: "2026-03",
        period_start: "2026-03-01T00:00:00Z",
        period_end: "2026-04-01T00:00:00Z",
        amount_paise: 499900,
        currency: "INR",
        status: "issued_unpaid",
        halt_episode_id: "he_1",
        generated_during_halt: true,
        created_at: "2026-03-09T00:00:00Z",
      },
    ];
    const html = renderToStaticMarkup(<BacklogTable invoices={invoices} />);
    expect(html).toContain("2026-02");
    expect(html).toContain("₹9,998");
    expect(html).toContain("Historical unpaid");
  });
});
