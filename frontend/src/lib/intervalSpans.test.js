import { describe, expect, it } from "vitest";
import { buildSpans, spanAt } from "../components/IntervalVisualizer";

const IV = [
  { name: "Warmup", duration: 600, powerTarget: { type: "range", min: 150, max: 190, unit: "watts" } },
  { name: "Sweet Spot 1", duration: 900, powerTarget: { type: "range", min: 277, max: 293, unit: "watts" } },
  { name: "Recovery", duration: 300 },
  { name: "Skipped", duration: 0 },
];
const ACTUAL = [{ interval_index: 1, actual_avg_w: 284.4, deviation_pct: 0, compliance: "on_target" }];

describe("interval hover spans", () => {
  const spans = buildSpans(IV, 314, ACTUAL);

  it("covers each interval's full width in minutes and skips zero-length ones", () => {
    expect(spans.map((s) => [s.name, s.start, s.end])).toEqual([["Warmup", 0, 10], ["Sweet Spot 1", 10, 25], ["Recovery", 25, 30]]);
    expect(spans[1].seconds).toBe(900);
  });

  it("attaches the computed result by interval index, and tolerates missing targets and results", () => {
    expect(spans[1].actual).toBe(284);
    expect(spans[1].compliance).toBe("on_target");
    expect(spans[2].target).toBeNull();
    expect(spans[0].actual).toBeNull();
  });

  it("finds the interval under any point, with boundaries belonging to the one starting", () => {
    expect(spanAt(spans, 0).name).toBe("Warmup");
    expect(spanAt(spans, 17.3).name).toBe("Sweet Spot 1");
    expect(spanAt(spans, 10).name).toBe("Sweet Spot 1");
    expect(spanAt(spans, 29.99).name).toBe("Recovery");
    expect(spanAt(spans, 30)).toBeNull();
  });
});
