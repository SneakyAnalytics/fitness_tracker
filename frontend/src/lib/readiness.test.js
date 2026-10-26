import { describe, expect, it } from "vitest";
import { todaysCall, withRollingMean } from "./readiness";

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

describe("withRollingMean", () => {
  const day = (n, hrv) => ({ date: `2026-10-${String(n).padStart(2, "0")}`, ...(hrv == null ? {} : { hrv }) });

  it("averages the trailing 7 days and waits for 3 readings", () => {
    const out = withRollingMean([day(1, 60), day(2, 70), day(3, 80), day(4, 50)], "hrv");
    expect(out.map((d) => d.hrvAvg)).toEqual([null, null, 70, 65]);
  });

  it("drops readings older than the window and tolerates gaps", () => {
    const days = [day(1, 100), day(2, 60), day(3), day(4, 60), day(5, 60), day(12, 60), day(13, 60), day(14, 60)];
    const out = withRollingMean(days, "hrv");
    expect(out[4].hrvAvg).toBe(70);                  // 100, 60, 60, 60
    expect(out[7].hrvAvg).toBe(60);                  // only Oct 12-14 are within 7 days
  });
});
