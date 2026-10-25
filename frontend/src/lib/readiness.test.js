import { describe, expect, it } from "vitest";
import { todaysCall } from "./readiness";

describe("todaysCall", () => {
  it("is a green light when nothing is flagged", () => {
    expect(todaysCall({ tsb: 5, flags: [] }).state).toBe("go");
    expect(todaysCall({ tsb: null, flags: [] }).state).toBe("go");
  });

  it("asks for an easy day on one warning sign or lowish form", () => {
    expect(todaysCall({ tsb: 0, flags: ["Resting HR is elevated vs baseline"] }).state).toBe("easy");
    const lowish = todaysCall({ tsb: -22, flags: [] });
    expect(lowish.state).toBe("easy");
    expect(lowish.reasons[0]).toMatch(/lowish/);
  });

  it("asks for rest on two signs or very low form", () => {
    expect(todaysCall({ tsb: 0, flags: ["HRV is suppressed", "Averaging 6.1h sleep"] }).state).toBe("rest");
    expect(todaysCall({ tsb: -31, flags: [] }).state).toBe("rest");
  });
});
