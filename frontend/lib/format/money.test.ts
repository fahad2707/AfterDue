import { describe, expect, it } from "vitest";

import { formatPaiseINR, formatRatio } from "@/lib/format/money";

describe("formatPaiseINR", () => {
  it("formats integer paise as INR rupees", () => {
    expect(formatPaiseINR(1499700)).toBe("₹14,997");
    expect(formatPaiseINR(49900)).toBe("₹499");
    expect(formatPaiseINR(0)).toBe("₹0");
  });

  it("rejects non-integers", () => {
    expect(() => formatPaiseINR(1499.7)).toThrow(/integer paise/);
  });
});

describe("formatRatio", () => {
  it("renders a percentage", () => {
    expect(formatRatio(0.650043)).toBe("65.0%");
  });
});
