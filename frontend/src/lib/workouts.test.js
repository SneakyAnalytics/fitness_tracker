import { describe, expect, it } from "vitest";
import { exerciseLookupUrl, flattenExercises, mergeDayWorkouts, resolvePowerTarget } from "./workouts";
import { parseSSEChunk } from "../api/client";

describe("resolvePowerTarget", () => {
  it("treats ramp values as % of FTP (previously showed 15,100W)", () => {
    const t = resolvePowerTarget(
      { start: { type: "percent_ftp", value: 50 }, end: { type: "percent_ftp", value: 75 } },
      300,
    );
    expect(t.label).toBe("150→225W ramp");
  });

  it("converts percent ranges and keeps watt ranges", () => {
    expect(resolvePowerTarget({ type: "range", min: 88, max: 93, unit: "percent_ftp" }, 300).label).toBe("264-279W");
    expect(resolvePowerTarget({ type: "range", min: 277, max: 293, unit: "watts" }, 300).label).toBe("277-293W");
  });
});

describe("exerciseLookupUrl", () => {
  it("encodes names with slashes and ampersands", () => {
    const url = exerciseLookupUrl("Bird Dog / Dead Bug & Plank");
    expect(url).toContain("Bird%20Dog%20%2F%20Dead%20Bug%20%26%20Plank");
    expect(new URL(url).searchParams.get("q")).toBe("Bird Dog / Dead Bug & Plank exercise demonstration");
  });
});

describe("mergeDayWorkouts", () => {
  const proposed = [
    { id: 10, date: "2026-09-29", name: "Sweet Spot 3x20", type: "bike", intervals: "[]" },
    { id: 11, date: "2026-09-29", name: "Core", type: "strength" },
  ];
  const completed = [
    { id: 882, date: "2026-09-29", title: "Zwift ride", proposed_workout_id: 10, metrics: { actual_tss: 98, actual_duration: 92 } },
    { id: 883, date: "2026-09-29", title: "Commute", proposed_workout_id: null, metrics: { actual_tss: 12, actual_duration: 25 } },
  ];

  it("shows a matched workout once, carrying its plan", () => {
    const day = mergeDayWorkouts(proposed, completed, "2026-09-29");
    expect(day.map((w) => w.key)).toEqual(["done-882", "done-883", "plan-11"]);
    expect(day[0].plan.name).toBe("Sweet Spot 3x20");
    expect(day[0].actualTSS).toBe(98);
  });
});

describe("flattenExercises", () => {
  it("flattens section exercises from a JSON string", () => {
    const sections = JSON.stringify([{ name: "Main", exercises: [{ name: "Squat" }, { name: "Row" }] }]);
    expect(flattenExercises({ sections }).map((e) => `${e.section}:${e.name}`)).toEqual(["Main:Squat", "Main:Row"]);
  });
});

describe("parseSSEChunk", () => {
  it("parses complete events and keeps the partial remainder", () => {
    const { events, rest } = parseSSEChunk('data: {"type":"text","text":"Hi"}\n\ndata: {"type":"st');
    expect(events).toEqual([{ type: "text", text: "Hi" }]);
    expect(rest).toBe('data: {"type":"st');
  });
});

import { movementTiming } from "./workouts";

describe("movementTiming", () => {
  it("uses structured duration and perSide", () => {
    expect(movementTiming({ sets: [{ duration: 45, perSide: true }] })).toEqual({ seconds: 45, perSide: true });
  });
  it("parses text like '30-40 seconds each side' (top of range)", () => {
    expect(movementTiming({ sets: [{ reps: "30-40 seconds each side" }] })).toEqual({ seconds: 40, perSide: true });
    expect(movementTiming({ sets: [{ reps: "1 min" }] })).toEqual({ seconds: 60, perSide: false });
  });
  it("returns null for rep-based work", () => {
    expect(movementTiming({ sets: [{ reps: 12, weight: "moderate" }] })).toBeNull();
    expect(movementTiming({ sets: [{ reps: "10 each leg" }] })).toBeNull();
  });
});

describe("mergeDayWorkouts with unconfirmed suggestions", () => {
  it("places a suggested match against its plan and labels suggested commutes", () => {
    const proposed = [{ id: 7, date: "2026-10-05", name: "Monday Flush", type: "bike" }];
    const completed = [
      { id: 1, date: "2026-10-05", title: "Zwift - Monday Flush", suggested_proposed_workout_id: 7, metrics: {} },
      { id: 2, date: "2026-10-05", title: "Cycling", suggested_label: "Commute to work", metrics: {} },
    ];
    const day = mergeDayWorkouts(proposed, completed, "2026-10-05");
    expect(day.map((w) => w.key)).toEqual(["done-1", "done-2"]); // plan 7 is not "not done"
    expect(day[0].plan.name).toBe("Monday Flush");
    expect(day[1].proposed_workout_name).toBe("Commute to work");
    expect(day[0].unconfirmed).toBe(true);
  });
});
