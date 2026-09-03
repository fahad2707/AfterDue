import { describe, expect, it } from "vitest";

import { provenanceLabel } from "@/lib/format/policy";

describe("provenanceLabel", () => {
  it("uses judge-facing wording", () => {
    expect(provenanceLabel("DOCUMENTED_PLATFORM_BEHAVIOR")).toBe(
      "Documented platform behavior",
    );
    expect(provenanceLabel("PRODUCT_DESIGN_ASSUMPTION")).toBe(
      "Product design assumption",
    );
    expect(provenanceLabel("SAFETY_GUARDRAIL")).toBe("Safety guardrail");
  });
});
