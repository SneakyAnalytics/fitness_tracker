import { describe, expect, it } from "vitest";
import { formLabel, formOn, lowestForm, plannedDayCount, projectionData } from "./loadProjection";

const lp = {
  history: [{ date: "2026-10-24", ctl: 60, atl: 70, tsb: -8 }, { date: "2026-10-25", ctl: 61, atl: 72, tsb: -10 }],
  projection: [
    { date: "2026-10-26", ctl: 62, atl: 75, tsb: -11, kind: "planned", tss: 90 },
    { date: "2026-10-27", ctl: 62, atl: 68, tsb: -13, kind: "planned", tss: 0 },
    { date: "2026-10-28", ctl: 62, atl: 64, tsb: -6, kind: "assumed", tss: 55 },
  ],
};

describe("projectionData", () => {
  it("joins the projection to the last real day so the dashed line starts where the solid one ends", () => {
    const rows = projectionData(lp);
    expect(rows).toHaveLength(5);
    expect(rows[1]).toMatchObject({ ctl: 61, ctlP: 61, tsbP: -10 });
    expect(rows[0].ctlP).toBeUndefined();
    expect(rows[2]).toMatchObject({ ctlP: 62, kind: "planned" });
    expect(rows[2].ctl).toBeUndefined();
  });
  it("is empty without history", () => {
    expect(projectionData(null)).toEqual([]);
    expect(projectionData({ history: [] })).toEqual([]);
  });
});

describe("form helpers", () => {
  it("labels form from TSB", () => {
    expect(formLabel(20)).toMatch(/very fresh/);
    expect(formLabel(8)).toBe("fresh");
    expect(formLabel(0)).toBe("balanced");
    expect(formLabel(-15)).toBe("building");
    expect(formLabel(-35)).toBe("deep fatigue");
  });
  it("finds form on a date, the lowest point, and how many days come from the plan", () => {
    expect(formOn(lp, "2026-10-27")).toEqual({ tsb: -13, ctl: 62, kind: "planned" });
    expect(formOn(lp, "2027-01-01")).toBeNull();
    expect(lowestForm(lp)).toEqual({ date: "2026-10-27", tsb: -13 });
    expect(plannedDayCount(lp)).toBe(2);
  });
});
