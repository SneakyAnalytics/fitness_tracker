import { describe, expect, it } from "vitest";
import { progressionRows, summarizeProgression, workVsPlan } from "./progression";

const s = (date, w, extra = {}) => ({ workout_date: date, work_avg_power: w, ...extra });

describe("summarizeProgression (watts)", () => {
  it("compares the latest session with the previous one and with the first", () => {
    const out = summarizeProgression([s("2026-09-08", 279), s("2026-09-22", 268), s("2026-10-06", 284)]);
    expect(out.delta).toBe(16);
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

  it("reports how far the latest session was from the plan", () => {
    const out = summarizeProgression([s("a", 280, { work_target_power: 283 }), s("b", 288, { work_target_power: 285 })]);
    expect(out.vsPlan).toBe(3);
    expect(summarizeProgression([s("a", 280)]).vsPlan).toBeNull();
  });
});

describe("% of FTP mode", () => {
  const sessions = [
    s("a", 305, { pct_ftp: 0.97, ftp: 315, work_target_power: 300 }),
    s("b", 310, { pct_ftp: 0.97, ftp: 320, work_target_power: 310 }),          // FTP rose, so the same watts are a lower %
    s("c", 312, { pct_ftp: 0.975, ftp: 320 }),
    s("d", 250, { pct_ftp: null, ftp: null }),                                   // no FTP on record: left out
  ];

  it("measures each session against the FTP it was prescribed against and drops unknowns", () => {
    const rows = progressionRows(sessions, "ftp");
    expect(rows.map((r) => r.value)).toEqual([97, 97, 97.5]);
    expect(rows[0].plan).toBeCloseTo(95.2, 1);
    expect(rows[2].plan).toBeNull();
  });

  it("uses a smaller threshold for a trend than watts do", () => {
    const rising = summarizeProgression([s("a", 1, { pct_ftp: 0.9 }), s("b", 1, { pct_ftp: 0.92 })], "ftp");
    expect(rising.trend).toBe("up");
    expect(rising.sinceFirst).toBe(2);
    expect(summarizeProgression([s("a", 1, { pct_ftp: 0.9 }), s("b", 1, { pct_ftp: 0.9100 })], "ftp").trend).toBe("flat");
  });
});

describe("workVsPlan", () => {
  const work = (avg, target) => ({ avg_power: avg, target_power: target, diff_w: avg - target, diff_pct: Math.round(((avg - target) / target) * 1000) / 10 });

  it("calls a ride within 3% of plan on plan", () => {
    expect(workVsPlan(work(284, 285), 314)).toEqual({ tone: "good", text: "Work intervals averaged 284 W against 285 W planned: on plan." });
  });

  it("says how far under or over, and points at FTP only when under", () => {
    const under = workVsPlan(work(276, 285.4), 314);
    expect(under.tone).toBe("warn");
    expect(under.text).toContain("9 W under (3.3%)");
    expect(under.text).toContain("FTP of 314 W");
    const over = workVsPlan(work(300, 285), 314);
    expect(over.text).toContain("15 W over (5.3%)");
    expect(over.text).not.toContain("FTP");
  });

  it("copes with no plan power and no summary", () => {
    expect(workVsPlan({ avg_power: 290, target_power: null })).toEqual({ tone: "plain", text: "Work intervals averaged 290 W." });
    expect(workVsPlan(null)).toBeNull();
  });
});
