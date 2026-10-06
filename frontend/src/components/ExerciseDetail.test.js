import { describe, expect, it } from "vitest";
import { formatWeight, prescription } from "./ExerciseDetail";

describe("exercise prescription", () => {
  it("groups identical sets and doesn't double up units", () => {
    const set = { reps: "10 each leg", weight: "moderate" };
    expect(prescription({ sets: [set, set, set] })).toBe("3 × 10 each leg · moderate");
  });

  it("adds 'reps' and 'lbs' only to plain numbers", () => {
    expect(prescription({ sets: [{ sets: 3, reps: 12, weight: 95 }] })).toBe("3 × 12 reps · 95 lbs");
    expect(prescription({ sets: [{ duration: 40, perSide: true, weight: "bodyweight" }] })).toBe("40s each side · bodyweight");
    expect(formatWeight("moderate (60-70% 1RM)")).toBe("moderate (60-70% 1RM)");
  });
});
