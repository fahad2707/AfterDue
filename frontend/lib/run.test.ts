import { describe, expect, it } from "vitest";

import { scopedQuery, withRun } from "@/lib/run";

describe("run scoping", () => {
  it("keeps navigation inside one run", () => {
    expect(withRun("/cases", "run_42_abc")).toBe("/cases?run=run_42_abc");
    expect(withRun("/", "run_42_abc")).toBe("/?run=run_42_abc");
  });

  it("scopes API queries by run_id", () => {
    expect(scopedQuery("run_42_abc")).toBe("run_id=run_42_abc");
    expect(scopedQuery("run x")).toBe("run_id=run%20x");
  });
});
