import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SyntheticBadge } from "@/components/console/SyntheticBadge";
import { EmptyState } from "@/components/ui/StateBlock";
import { StrategyComparison } from "@/components/dashboard/StrategyComparison";
import type { StrategyMetrics } from "@/types/api";

describe("SyntheticBadge", () => {
  it("renders a visible synthetic label", () => {
    const html = renderToStaticMarkup(<SyntheticBadge />);
    expect(html).toContain("Synthetic prototype");
    expect(html).toContain("synthetic-badge");
  });
});

describe("missing run empty state", () => {
  it("points the user to simulation", () => {
    const html = renderToStaticMarkup(
      <EmptyState
        title="No simulation runs"
        body="Generate a synthetic world first."
        href="/simulate"
        action="Open simulation"
      />,
    );
    expect(html).toContain("No simulation runs");
    expect(html).toContain("/simulate");
  });
});

describe("strategy comparison", () => {
  it("renders recovered revenue from backend metrics", () => {
    const naive: StrategyMetrics = {
      strategy_name: "naive",
      eligible_cases: 8,
      intervention_budget: 8,
      interventions_used: 5,
      revenue_at_risk_paise: 7998400,
      revenue_recovered_paise: 5199300,
      recovery_yield: 0.65,
      recovered_case_count: 4,
      failed_intervention_count: 1,
      escalation_count: 3,
      no_action_count: 0,
      revenue_per_intervention_paise: 1,
      revenue_per_100_cases_paise: 1,
      unnecessary_intervention_count: 1,
      incremental_revenue_paise: 100,
      action_cost_paise: 16000,
      synthetic: true,
    };
    const html = renderToStaticMarkup(
      <StrategyComparison
        results={{
          naive,
          rule_based: { ...naive, strategy_name: "rule_based" },
          reclaim: {
            ...naive,
            strategy_name: "reclaim",
            revenue_recovered_paise: 5999300,
          },
        }}
      />,
    );
    expect(html).toContain("₹51,993");
    expect(html).toContain("₹59,993");
    expect(html).toContain("Naive");
    expect(html).toContain("Rule-based");
    expect(html).toContain("AfterDue");
    expect(html).not.toContain("AI confidence");
  });
});
