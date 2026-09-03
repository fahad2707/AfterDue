import { describe, expect, it, vi, afterEach } from "vitest";

import {
  TOUR_QUERY,
  TOUR_SCENE_COUNT,
  TOUR_STORAGE_KEY,
  clearTourSeen,
  markTourSeen,
  tourSeen,
} from "@/lib/tour";

describe("tour storage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses afterdue_tour_seen and eight scenes", () => {
    expect(TOUR_STORAGE_KEY).toBe("afterdue_tour_seen");
    expect(TOUR_QUERY).toBe("tour");
    expect(TOUR_SCENE_COUNT).toBe(8);
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
    expect(tourSeen()).toBe(false);
    markTourSeen();
    expect(tourSeen()).toBe(true);
    clearTourSeen();
    expect(tourSeen()).toBe(false);
  });
});
