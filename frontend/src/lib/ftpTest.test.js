import { describe, expect, it } from "vitest";
import { ftpTestStatus, spanLabel } from "./ftpTest";

const day = (s) => new Date(`${s}T12:00:00`);

describe("ftpTestStatus", () => {
  it("is fresh just after a test, with the next one due six weeks on", () => {
    const s = ftpTestStatus({ last_test_or_race: "2026-10-20" }, day("2026-10-26"));
    expect(s.state).toBe("fresh");
    expect(s.weeks).toBe(0.9);
    expect(s.dueLabel).toBe("Dec 1");
    expect(s.daysLeft).toBe(36);
    expect(s.kind).toBe("test");
  });

  it("moves to soon at four weeks and due at six", () => {
    expect(ftpTestStatus({ last_test_or_race: "2026-10-20" }, day("2026-11-20")).state).toBe("soon");
    const due = ftpTestStatus({ last_test_or_race: "2026-10-20" }, day("2026-12-03"));
    expect(due.state).toBe("due");
    expect(due.daysLeft).toBeLessThan(0);
    expect(due.progress).toBe(1);
  });

  it("falls back to the last FTP change, and says when there is nothing to go on", () => {
    expect(ftpTestStatus({ changed_on: "2026-09-01" }, day("2026-10-26")).kind).toBe("change");
    expect(ftpTestStatus({}, day("2026-10-26")).state).toBe("unknown");
    expect(ftpTestStatus(null).state).toBe("unknown");
  });
});

describe("spanLabel", () => {
  it("uses days under two weeks and weeks beyond", () => {
    expect(spanLabel(0)).toBe("0 days");
    expect(spanLabel(1)).toBe("1 day");
    expect(spanLabel(6)).toBe("6 days");
    expect(spanLabel(36)).toBe("5.1 weeks");
    expect(spanLabel(-3)).toBe("3 days");
  });
});
