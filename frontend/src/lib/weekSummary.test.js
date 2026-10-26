import { describe, expect, it } from "vitest";
import { summarizeReview, summarizeWeek } from "./weekSummary";

const planned = [
  { id: 1, date: "2026-10-12", plannedTSS_min: 28, plannedTSS_max: 33 },
  { id: 2, date: "2026-10-14", plannedTSS_min: 72, plannedTSS_max: 78 },
  { id: 3, date: "2026-10-16", plannedTSS_min: 33, plannedTSS_max: 38 },
  { id: 4, date: "2026-10-17", plannedTSS_min: 26, plannedTSS_max: 31 },
];

describe("summarizeWeek", () => {
  const completed = [
    { id: 10, date: "2026-10-12", proposed_workout_id: 1, metrics: { actual_tss: 30 } },
    { id: 11, date: "2026-10-13", metrics: { actual_tss: 15.4 } },                                  // a commute: unplanned
    { id: 12, date: "2026-10-14", suggested_proposed_workout_id: 2, metrics: { actual_tss: 74 } },  // only suggested so far
  ];
  const plan = { plannedTSS_min: 327, plannedTSS_max: 379 };
  const weather = { "2026-10-15": { rain_pct: 80 }, "2026-10-16": { rain_pct: 10 }, "2026-10-17": { rain_pct: 60 }, "2026-10-13": { rain_pct: 90 } };

  it("counts matched, unplanned, missed and upcoming sessions against the plan", () => {
    const w = summarizeWeek({ proposed: planned, completed, plan, weather, today: "2026-10-15" });
    expect(w).toMatchObject({ tss: 119, planned: 4, matched: 2, unplanned: 1, missed: 0, upcoming: 2 });
    expect(w.band).toEqual({ min: 327, max: 379 });
  });

  it("flags planned sessions in the past that nobody did, and only the wet days still ahead", () => {
    const w = summarizeWeek({ proposed: planned, completed: completed.slice(0, 1), plan, weather, today: "2026-10-15" });
    expect(w.missed).toBe(1);                                     // the Oct 14 session
    expect(w.wetDays).toEqual(["2026-10-15", "2026-10-17"]);      // Oct 13 is behind us, Oct 16 is dry
  });

  it("doesn't count a zero-minute rest day as a session to do or miss", () => {
    const withRest = [...planned, { id: 5, date: "2026-10-13", plannedDuration: 0, name: "Complete Rest Day" }];
    const w = summarizeWeek({ proposed: withRest, completed: [], plan, weather, today: "2026-10-16" });
    expect(w.planned).toBe(4);
    expect(w.missed).toBe(2);                                    // Oct 12 and Oct 14, not the rest day
  });

  it("copes with no plan and no data", () => {
    expect(summarizeWeek({ today: "2026-10-15" })).toMatchObject({ tss: 0, band: null, planned: 0, matched: 0, wetDays: [] });
  });
});

describe("summarizeReview", () => {
  it("counts confirmed and suggested rows with total hours and TSS", () => {
    const rows = [
      { status: "confirmed", minutes: 60, tss: 40 }, { status: "suggested", minutes: 30, tss: 20.4 },
      { status: "suggested", minutes: 20, tss: null }, { status: "none", minutes: 15, tss: 5 },
    ];
    expect(summarizeReview(rows)).toEqual({ total: 4, confirmed: 1, toConfirm: 2, other: 1, hours: 2.1, tss: 65 });
    expect(summarizeReview()).toMatchObject({ total: 0, hours: 0 });
  });
});
