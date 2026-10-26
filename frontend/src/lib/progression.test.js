import { describe, expect, it } from "vitest";
import { summarizeProgression } from "./progression";

const s = (date, w) => ({ workout_date: date, work_avg_power: w });

describe("summarizeProgression", () => {
  it("compares the latest session with the previous one and with the first", () => {
    const out = summarizeProgression([s("2026-09-08", 279), s("2026-09-22", 268), s("2026-10-06", 284)]);
    expect(out.deltaW).toBe(16);
    expect(out.sinceFirst).toBe(5);
    expect(out.trend).toBe("up");
    expect(out.best.workout_date).toBe("2026-10-06");
  });

  it("handles one session, flat and falling runs, and empty input", () => {
    expect(summarizeProgression([s("2026-10-06", 284)]).trend).toBe("new");
    expect(summarizeProgression([s("a", 300), s("b", 302)]).trend).toBe("flat");
    expect(summarizeProgression([s("a", 300), s("b", 290)]).trend).toBe("down");
    expect(summarizeProgression([])).toBeNull();
  });
});
