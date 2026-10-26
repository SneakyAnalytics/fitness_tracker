import { describe, expect, it } from "vitest";
import { bikeArtKey, sessionArtKey } from "../components/CoachLogo";

describe("bike session badges", () => {
  it("picks the key-session badge from the workout name", () => {
    expect(bikeArtKey("Sweet Spot Progression — 3x15min @ 88-93% FTP")).toBe("sweet_spot");
    expect(bikeArtKey("KEY SESSION - Sweet Spot Sharpener 2x12min @ 90% FTP")).toBe("sweet_spot");
    expect(bikeArtKey("Over-Under Threshold: 4x8min Alternating 95%/105% FTP")).toBe("over_under");
    expect(bikeArtKey("Threshold Pyramid — 3-5-7-5-3min @ FTP")).toBe("threshold");
    expect(bikeArtKey("VO2max Development — 5x4min")).toBe("vo2max");
    expect(bikeArtKey("Tempo Progression: 3x15min @ 76-85% FTP")).toBe("tempo");
    expect(bikeArtKey("Aerobic Maintenance - Zone 2 Steady")).toBe("endurance");
    expect(bikeArtKey("Endurance Base — Zone 2 Steady State")).toBe("endurance");
  });

  it("keeps the plain cycling badge for commutes, recovery spins and unnamed rides", () => {
    expect(bikeArtKey("Bike Commute - Easy Z1/Z2")).toBe("cycling");
    expect(bikeArtKey("Monday Flush — Active Recovery Spin")).toBe("cycling");
    expect(bikeArtKey("Gifford Pinchot Gravel — 54mi")).toBe("cycling");
    expect(bikeArtKey("")).toBe("cycling");
  });

  it("only affects bike sessions", () => {
    expect(sessionArtKey("bike", "Sweet Spot Progression")).toBe("sweet_spot");
    expect(sessionArtKey("Bike", "Threshold intervals")).toBe("threshold");
    expect(sessionArtKey("strength", "Tempo core work")).toBe("strength");
    expect(sessionArtKey("other", "Sauna Recovery")).toBe("sauna");
  });
});
