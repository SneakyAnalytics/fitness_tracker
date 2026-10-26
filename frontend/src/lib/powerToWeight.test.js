import { describe, expect, it } from "vitest";
import { weightChange, wkgProgress } from "./powerToWeight";

describe("wkgProgress", () => {
  it("says what is left to reach the target two ways", () => {
    const r = wkgProgress({ wkg: 3.8, target: 4.2, ftp: 320, weight_kg: 84, watts_needed: 33, kg_to_lose: 7.8 });
    expect(r.pct).toBe(90);
    expect(r.reached).toBe(false);
    expect(r.sentence).toBe("To reach 4.2 W/kg: 33 W more at 84 kg, or 7.8 kg lighter at 320 W.");
  });
  it("celebrates once past the target and caps the bar at 100", () => {
    const r = wkgProgress({ wkg: 4.1, target: 4.0, ftp: 320, weight_kg: 78, watts_needed: 0, kg_to_lose: 0 });
    expect(r).toEqual({ pct: 100, reached: true, sentence: "Past the 4.0 W/kg target." });
  });
  it("works without a target and returns null without data", () => {
    expect(wkgProgress({ wkg: 3.9 })).toEqual({ pct: null, reached: false, sentence: null });
    expect(wkgProgress({})).toBeNull();
    expect(wkgProgress(null)).toBeNull();
  });
});

describe("weightChange", () => {
  it("is the drift from the first to the last weekly average", () => {
    expect(weightChange({ weekly: [{ kg: 80.4 }, { kg: 79.9 }, { kg: 79.1 }] })).toBe(-1.3);
    expect(weightChange({ weekly: [{ kg: 80 }] })).toBeNull();
  });
});
