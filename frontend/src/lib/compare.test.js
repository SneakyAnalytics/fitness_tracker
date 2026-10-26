import { describe, expect, it } from "vitest";
import { defaultPair, intervalRows, mergeSeries, similarTo, summaryRows } from "./compare";

describe("defaultPair", () => {
  it("pairs the newest ride with the previous one of the same name", () => {
    const rides = [{ id: 5, name: "Sweet Spot 3x15" }, { id: 4, name: "Easy Spin" }, { id: 3, name: "sweet spot 3x15" }];
    expect(defaultPair(rides)).toEqual([5, 3]);
  });
  it("falls back to the previous ride, and copes with too few rides", () => {
    expect(defaultPair([{ id: 2, name: "A" }, { id: 1, name: "B" }])).toEqual([2, 1]);
    expect(defaultPair([{ id: 1, name: "A" }])).toEqual([1, null]);
    expect(defaultPair([])).toEqual([null, null]);
  });
});

describe("mergeSeries", () => {
  it("puts both rides on one minute axis even when their steps differ", () => {
    const a = { step_sec: 30, power: [100, 110, 120], hr: [] };
    const b = { step_sec: 60, power: [90, 95], hr: [130, 131] };
    expect(mergeSeries(a, b)).toEqual([
      { min: 0, a: 100, b: 90, bHr: 130 },
      { min: 0.5, a: 110 },
      { min: 1, a: 120, b: 95, bHr: 131 },
    ]);
  });
  it("works with a single ride", () => {
    expect(mergeSeries({ step_sec: 60, power: [1], hr: [] }, null)).toEqual([{ min: 0, a: 1 }]);
  });
});

describe("summaryRows", () => {
  it("shows both values and the difference, hiding rows neither ride has", () => {
    const a = { duration_sec: 3600, summary: { avg_power: 200, np: 210, tss: 60, avg_hr: null } };
    const b = { duration_sec: 3000, summary: { avg_power: 190, np: 205, tss: 55 } };
    const rows = summaryRows(a, b);
    expect(rows.find((r) => r.label === "Duration")).toMatchObject({ a: 60, b: 50, delta: 10 });
    expect(rows.find((r) => r.label === "Average power")).toMatchObject({ a: 200, b: 190, delta: 10 });
    expect(rows.find((r) => r.label === "Average heart rate")).toBeUndefined();
  });
});

describe("intervalRows", () => {
  it("lines intervals up by position", () => {
    const rows = intervalRows({ intervals: [{ name: "Work 1", actual_avg_w: 300 }] }, { intervals: [{ name: "Work 1", actual_avg_w: 290 }, { name: "Work 2", actual_avg_w: 288 }] });
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ index: 1, name: "Work 1" });
    expect(rows[1].a).toBeNull();
  });
});

describe("similarTo", () => {
  const rides = [{ id: 5, name: "SS" }, { id: 4, name: "Easy" }, { id: 3, name: "ss" }, { id: 2, name: "Easy" }];
  it("finds the previous ride with the same name", () => {
    expect(similarTo(rides, 5)).toBe(3);
    expect(similarTo(rides, "4")).toBe(2);
  });
  it("falls back to the next older ride, or the newest other ride for the oldest", () => {
    expect(similarTo(rides, 3)).toBe(2);
    expect(similarTo(rides, 2)).toBe(5);
    expect(similarTo(rides, 99)).toBeNull();
  });
});
