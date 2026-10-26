/**
 * Today's call from the readiness flags and training form (TSB):
 *   rest  two or more warning signs, or very low form
 *   easy  one warning sign, or lowish form
 *   go    nothing flagged
 */
export function todaysCall({ tsb, flags = [] }) {
  const reasons = [...flags];
  if (tsb != null && tsb <= -25) reasons.push(`Form is very low (TSB ${Math.round(tsb)}): fatigue is well ahead of fitness`);
  const veryLow = tsb != null && tsb <= -30;
  if (reasons.length >= 2 || veryLow) {
    return { state: "rest", headline: "Rest or keep it very easy", art: "rest", reasons };
  }
  if (reasons.length === 1 || (tsb != null && tsb <= -20)) {
    if (reasons.length === 0) reasons.push(`Form is lowish (TSB ${Math.round(tsb)})`);
    return { state: "easy", headline: "Easy day: keep it in Zone 1-2", art: "mobility", reasons };
  }
  return { state: "go", headline: "Green light: train as planned", art: "run", reasons: ["HRV, resting HR, sleep and form all look fine"] };
}

/**
 * Adds `${key}Avg` to each day: the mean of the readings in the trailing `window` days (needs at least
 * `minCount`). Daily wearable readings swing a lot; the average is what the dashboard flags are based on.
 */
export function withRollingMean(days, key, window = 7, minCount = 3) {
  const dayMs = 86400000;
  return days.map((d, i) => {
    const t = Date.parse(d.date);
    const inWindow = days.slice(0, i + 1).filter((x) => x[key] != null && t - Date.parse(x.date) < window * dayMs);
    const avg = inWindow.length >= minCount ? inWindow.reduce((sum, x) => sum + x[key], 0) / inWindow.length : null;
    return { ...d, [`${key}Avg`]: avg == null ? null : Math.round(avg * 10) / 10 };
  });
}
