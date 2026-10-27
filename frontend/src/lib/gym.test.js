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

import { cuesFor, describeSession, logEntry, suggestWeight, targetRepsTop } from "./gym";

describe("targetRepsTop", () => {
  it("takes the top of a range and ignores timed work", () => {
    expect(targetRepsTop({ reps: "8-10" })).toBe(10);
    expect(targetRepsTop({ reps: 12 })).toBe(12);
    expect(targetRepsTop({ reps: "12 each direction, each leg" })).toBe(12);
    expect(targetRepsTop({ reps: "30 seconds" })).toBeNull();
    expect(targetRepsTop({})).toBeNull();
  });
});

describe("suggestWeight", () => {
  const sets = (w, reps) => ({ sets: reps.map((r) => ({ weight: w, reps: r })) });
  it("goes up about 5% once every set hits the top of the range", () => {
    expect(suggestWeight(sets(45, [10, 10, 10]), 10)).toMatchObject({ weight: 47.5, change: "up" });
    expect(suggestWeight(sets(100, [10, 10, 10]), 10)).toMatchObject({ weight: 105, change: "up" });
    expect(suggestWeight(sets(20, [12, 12]), 12).weight).toBe(22.5);   // never less than +2.5
  });
  it("holds when a set fell short, or when there is no target to judge against", () => {
    expect(suggestWeight(sets(45, [10, 10, 8]), 10)).toMatchObject({ weight: 45, change: "hold" });
    expect(suggestWeight(sets(45, [10, 10]), null)).toMatchObject({ weight: 45, change: "hold" });
  });
  it("never adds weight from an old log that only recorded total reps", () => {
    expect(suggestWeight({ sets: [{ weight: 45, reps: 24, total: true }] }, 10)).toMatchObject({ weight: 45, change: "hold" });
  });
  it("judges only the sets at the top weight, and needs a weight to build on", () => {
    expect(suggestWeight({ sets: [{ weight: 40, reps: 8 }, { weight: 45, reps: 10 }] }, 10).weight).toBe(47.5);
    expect(suggestWeight({ sets: [{ weight: null, reps: 20 }] }, 20)).toBeNull();
    expect(suggestWeight(null, 10)).toBeNull();
  });
});

describe("describeSession, cuesFor, logEntry", () => {
  it("describes what was lifted", () => {
    expect(describeSession({ sets: [{ weight: 45, reps: 10 }, { weight: 45, reps: 8 }] })).toBe("45 lb × 10, 8");
    expect(describeSession({ sets: [{ weight: null, reps: 24 }] })).toBe("bodyweight × 24");
    expect(describeSession({ sets: [{ weight: 45, reps: 24, total: true }] })).toBe("45 lb × 24 total");
    expect(describeSession(null)).toBe("");
  });
  it("collects the cues for the set you are on plus the exercise's own, once each", () => {
    const ex = { cues: ["Chest tall"], sets: [{ sets: 2, notes: ["Elbows in", "Chest tall"] }, { notes: ["Slow down"] }] };
    expect(cuesFor(ex, 0)).toEqual(["Elbows in", "Chest tall"]);
    expect(cuesFor(ex, 2)).toEqual(["Slow down", "Chest tall"]);
    expect(cuesFor({ name: "x" }, 0)).toEqual([]);
  });
  it("saves only sets that have something in them", () => {
    const entry = logEntry({ name: "Goblet Squat" }, [{ weight: "45", reps: "10" }, { weight: "50", reps: "8" }, { weight: "", reps: "" }]);
    expect(entry).toMatchObject({ name: "Goblet Squat", reps: "10, 8", weight: "50" });
    expect(entry.sets).toHaveLength(2);
    expect(logEntry({ name: "x" }, [{ weight: "", reps: "" }])).toBeNull();
    expect(logEntry({ name: "Plank" }, [{ weight: "", reps: "30" }]).weight).toBe("");
  });
});

import { saveErrorMessage } from "./gym";

describe("saveErrorMessage", () => {
  it("explains an unreachable server in plain words and keeps real server errors specific", () => {
    expect(saveErrorMessage({ message: "Network Error" })).toMatch(/Tailscale/);
    expect(saveErrorMessage({ response: { status: 500, data: { detail: "Failed to save" } } })).toBe("The server refused the save (500: Failed to save).");
    expect(saveErrorMessage({ response: { status: 502 } })).toBe("The server refused the save (502).");
  });
});
