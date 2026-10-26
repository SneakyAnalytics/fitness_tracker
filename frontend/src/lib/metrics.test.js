import { describe, expect, it } from "vitest";
import { METRICS, metricById } from "./metrics";

describe("metric glossary", () => {
  it("has every field the hover card and the guide page need", () => {
    const ids = new Set();
    for (const m of METRICS) {
      expect(ids.has(m.id)).toBe(false);
      ids.add(m.id);
      for (const key of ["name", "short", "read", "what", "how", "coach", "limits"]) expect(m[key], `${m.id}.${key}`).toBeTruthy();
      expect(m.ranges.length).toBeGreaterThan(1);
    }
    for (const id of ["ctl", "atl", "tsb", "ramp", "ftp", "hrv", "sleep"]) expect(metricById(id)).toBeTruthy();
  });

  it("reads today's number in plain language", () => {
    const tsb = metricById("tsb").interpret;
    expect(tsb(10)).toBe("Fresh");
    expect(tsb(-12)).toBe("Productive fatigue");
    expect(tsb(-35)).toMatch(/Deep/);
    expect(metricById("ramp").interpret(3)).toBe("In the build range");
    expect(metricById("sleep").interpret(6.4)).toMatch(/debt/);
    expect(metricById("hrv").interpret(67, { changePct: -12 })).toMatch(/suppressed/);
    expect(metricById("tsb").interpret(null)).toBeNull();
  });
});
