import { describe, expect, it } from "vitest";
import { format } from "date-fns";
import { parseWeekParam } from "./useWeekParam";

describe("parseWeekParam", () => {
  it("snaps any date to the Monday of its week", () => {
    expect(format(parseWeekParam("2026-10-07"), "yyyy-MM-dd")).toBe("2026-10-05");
    expect(format(parseWeekParam("2026-10-11"), "yyyy-MM-dd")).toBe("2026-10-05"); // Sunday belongs to the week before
    expect(format(parseWeekParam("2026-10-12"), "yyyy-MM-dd")).toBe("2026-10-12");
  });

  it("ignores missing or malformed values", () => {
    expect(parseWeekParam(null)).toBeNull();
    expect(parseWeekParam("")).toBeNull();
    expect(parseWeekParam("last-week")).toBeNull();
  });
});
