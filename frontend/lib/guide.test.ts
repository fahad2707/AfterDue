import { describe, expect, it, vi, afterEach } from "vitest";

import {
  GUIDE_QUERY,
  GUIDE_STEPS,
  GUIDE_STORAGE_KEY,
  clearGuideSeen,
  guideSeen,
  markGuideSeen,
} from "@/lib/guide";

describe("usage guide", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("covers the live console options", () => {
    expect(GUIDE_STORAGE_KEY).toBe("afterdue_guide_seen");
    expect(GUIDE_QUERY).toBe("guide");
    expect(GUIDE_STEPS.map((step) => step.id)).toEqual([
      "nav-overview",
      "overview-metrics",
      "nav-cases",
      "case-table",
      "nav-simulate",
      "nav-evaluation",
      "nav-model",
      "nav-policy",
    ]);
  });

  it("reads and writes localStorage", () => {
    const store = new Map<string, string>();
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (key: string) => store.get(key) ?? null,
        setItem: (key: string, value: string) => {
          store.set(key, value);
        },
        removeItem: (key: string) => {
          store.delete(key);
        },
      },
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => true,
    });
    expect(guideSeen()).toBe(false);
    markGuideSeen();
    expect(guideSeen()).toBe(true);
    clearGuideSeen();
    expect(guideSeen()).toBe(false);
  });
});
