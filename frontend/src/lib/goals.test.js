import { describe, expect, it } from "vitest";
import { medalLabel } from "./goals";

describe("medalLabel", () => {
  it("keeps the event name and drops the verb and the detail", () => {
    expect(medalLabel("Complete C2C (Corvallis to Coast) - 65 miles, 5,700ft elevation")).toBe("C2C");
    expect(medalLabel("Complete a 100-mile (century) ride before the season ends")).toBe("100-mile");
    expect(medalLabel("Gifford Pinchot Gravel — 54 mi / 5,200 ft")).toBe("Gifford Pinchot Gravel");
  });

  it("shortens long names with an ellipsis and survives empty input", () => {
    expect(medalLabel("Zwift ramp/FTP test to confirm 320W+ (4.0 W/kg)")).toBe("Zwift ramp/FTP test…");
    expect(medalLabel("Multi-day Alberta Rockies trip - ~50 miles/day")).toBe("Multi-day Alberta Rockies…");
    expect(medalLabel("")).toBe("Goal");
    expect(medalLabel(null)).toBe("Goal");
  });
});
