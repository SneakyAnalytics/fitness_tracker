import { describe, expect, it } from "vitest";
import { describeWeather, isWet } from "./weather";

describe("describeWeather", () => {
  it("maps WMO codes to icons", () => {
    expect(describeWeather(0).icon).toBe("sun");
    expect(describeWeather(2).icon).toBe("cloud-sun");
    expect(describeWeather(45).icon).toBe("fog");
    expect(describeWeather(61).icon).toBe("rain");
    expect(describeWeather(73).icon).toBe("snow");
    expect(describeWeather(95).icon).toBe("storm");
    expect(describeWeather(null).label).toBe("");
  });

  it("treats 50% or more chance of rain as wet", () => {
    expect(isWet({ rain_pct: 50 })).toBe(true);
    expect(isWet({ rain_pct: 49 })).toBe(false);
    expect(isWet(undefined)).toBe(false);
  });
});
