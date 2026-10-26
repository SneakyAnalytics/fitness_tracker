import { describe, expect, it } from "vitest";
import { clock, expandSets, restSeconds, sessionProgress } from "./gym";

describe("expandSets", () => {
  it("repeats each set definition by its count", () => {
    const ex = { sets: [{ sets: 3, reps: "10" }, { reps: "8", weight: "heavy" }] };
    const sets = expandSets(ex);
    expect(sets).toHaveLength(4);
    expect(sets[0].reps).toBe("10");
    expect(sets[3].weight).toBe("heavy");
  });
  it("treats an exercise with no set detail as a single set", () => {
    expect(expandSets({ name: "Plank" })).toHaveLength(1);
    expect(expandSets({ sets: [] })).toHaveLength(1);
  });
});

describe("restSeconds", () => {
  it("uses the prescribed rest, else the default, and caps absurd values", () => {
    expect(restSeconds({ sets: [{ reps: 10, restBetweenSets: 90 }] })).toBe(90);
    expect(restSeconds({ sets: [{ restTime: 45 }] })).toBe(45);
    expect(restSeconds({ sets: [{ reps: 10 }] })).toBe(60);
    expect(restSeconds({ sets: [{ restBetweenSets: 5000 }] })).toBe(600);
    expect(restSeconds({}, 30)).toBe(30);
  });
});

describe("clock and progress", () => {
  it("formats a countdown", () => {
    expect(clock(75)).toBe("1:15");
    expect(clock(5)).toBe("0:05");
    expect(clock(-3)).toBe("0:00");
  });
  it("counts finished sets across the session, never past an exercise's total", () => {
    const ex = [{ sets: [{ sets: 3 }] }, { sets: [{ sets: 1 }] }];
    expect(sessionProgress(ex, [3, 0])).toBe(0.75);
    expect(sessionProgress(ex, [9, 1])).toBe(1);
    expect(sessionProgress([], [])).toBe(0);
  });
});
