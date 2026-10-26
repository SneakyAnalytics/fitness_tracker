import { describe, expect, it } from "vitest";
import { groupByDay, intervalLines, planAsText, planNotes, sessionDetail } from "./planText";

const bike = {
  name: "KEY SESSION - Sweet Spot", type: "bike", date: "2026-10-14", plannedDuration: 80, plannedTSS_min: 72, plannedTSS_max: 78,
  intervals: JSON.stringify([
    { name: "Warmup", duration: 900, powerTarget: { type: "range", min: 150, max: 190, unit: "watts" } },
    { name: "Opener 1", duration: 60, powerTarget: { type: "range", min: 255, max: 270, unit: "watts" } },
    { name: "Sweet Spot 1", duration: 720, powerTarget: { type: "range", min: 277, max: 290, unit: "watts" } },
    { name: "Recovery", duration: 420, powerTarget: { type: "range", min: 165, max: 180, unit: "watts" } },
    { name: "Sweet Spot 2", duration: 720, powerTarget: { type: "range", min: 280, max: 293, unit: "watts" } },
  ]),
};
const mobility = { name: "Lower Back & Hip Reset", type: "mobility", date: "2026-10-12", plannedDuration: 30,
  sections: JSON.stringify([{ name: "Flow", exercises: [{ name: "Cat-Cow" }, { name: "Child's Pose" }] }]) };

describe("plan text", () => {
  it("lists only the sustained hard intervals of a ride", () => {
    expect(intervalLines(JSON.parse(bike.intervals), 314)).toEqual(["12:00 @ 277-290W", "12:00 @ 280-293W"]);
  });

  it("describes strength and mobility sessions by their movements", () => {
    expect(sessionDetail(mobility, 314)).toBe("2 movements: Cat-Cow, Child's Pose");
  });

  it("reads the week's focus from JSON notes, or plain text", () => {
    expect(planNotes({ notes: JSON.stringify({ weekFocus: "Recovery week", specialConsiderations: "Travel Friday" }) }))
      .toEqual({ focus: "Recovery week", considerations: "Travel Friday" });
    expect(planNotes({ notes: "Just a note" }).focus).toBe("Just a note");
    expect(planNotes(null)).toEqual({ focus: "", considerations: "" });
  });

  it("covers all seven days, with rest days, in order", () => {
    const days = groupByDay([bike, mobility], "2026-10-12");
    expect(days.map((d) => d.label)).toEqual(["Mon Oct 12", "Tue Oct 13", "Wed Oct 14", "Thu Oct 15", "Fri Oct 16", "Sat Oct 17", "Sun Oct 18"]);
    expect(days[0].sessions).toHaveLength(1);
    expect(days[1].sessions).toHaveLength(0);
  });

  it("builds a paste-able summary of the week", () => {
    const text = planAsText({ weekStart: "2026-10-12", plan: { plannedTSS_min: 327, plannedTSS_max: 379, notes: JSON.stringify({ weekFocus: "Recovery week" }) }, workouts: [bike, mobility], ftp: 314 });
    expect(text.split("\n")[0]).toBe("Week of Oct 12 to Oct 18, 2026 · plan 327-379 TSS · FTP 314 W");
    expect(text).toContain("Focus: Recovery week");
    expect(text).toContain("Mon Oct 12\n  - Lower Back & Hip Reset · mobility · 30 min");
    expect(text).toContain("Tue Oct 13\n  Rest");
    expect(text).toContain("12:00 @ 277-290W  |  12:00 @ 280-293W");
  });
});
