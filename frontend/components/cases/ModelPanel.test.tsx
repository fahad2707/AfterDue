import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ModelPanel } from "@/components/cases/ModelPanel";
import type { ModelAnalysis } from "@/types/api";

const analysis: ModelAnalysis = {
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
};

describe("ModelPanel", () => {
  it("shows economic estimates, not AI confidence", () => {
    const html = renderToStaticMarkup(<ModelPanel analysis={analysis} />);
    expect(html).toContain("₹4,648");
    expect(html).toContain("₹10,048");
    expect(html).toContain("+36.0 pp");
    expect(html).toContain("₹5,390");
    expect(html).toContain("send payment link");
    expect(html).toContain("m5-v1");
    expect(html).not.toContain("AI confidence");
    expect(html).toContain("not guaranteed recovery");
  });
});
