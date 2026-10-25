/** WMO weather codes (as returned by the forecast service) -> a short word and which icon to draw. */
export function describeWeather(code) {
  if (code == null) return { label: "", icon: "cloud" };
  if (code === 0) return { label: "Clear", icon: "sun" };
  if (code <= 2) return { label: "Partly cloudy", icon: "cloud-sun" };
  if (code === 3) return { label: "Overcast", icon: "cloud" };
  if (code <= 48) return { label: "Fog", icon: "fog" };
  if (code <= 57) return { label: "Drizzle", icon: "rain" };
  if (code <= 67) return { label: "Rain", icon: "rain" };
  if (code <= 77) return { label: "Snow", icon: "snow" };
  if (code <= 82) return { label: "Showers", icon: "rain" };
  if (code <= 86) return { label: "Snow showers", icon: "snow" };
  return { label: "Thunderstorm", icon: "storm" };
}

/** Wet enough that an outdoor ride or a bike commute deserves a thought. */
export const isWet = (day) => (day?.rain_pct ?? 0) >= 50;
