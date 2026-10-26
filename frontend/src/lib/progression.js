/** Summary of a run of sessions of one kind, oldest first: latest vs previous, best ever, and the overall direction. */
export function summarizeProgression(sessions) {
  if (!sessions?.length) return null;
  const latest = sessions[sessions.length - 1];
  const previous = sessions.length > 1 ? sessions[sessions.length - 2] : null;
  const first = sessions[0];
  const best = sessions.reduce((a, b) => (b.work_avg_power > a.work_avg_power ? b : a));
  const deltaW = previous ? Math.round(latest.work_avg_power - previous.work_avg_power) : null;
  const sinceFirst = sessions.length > 1 ? Math.round(latest.work_avg_power - first.work_avg_power) : null;
  let trend = "new";
  if (sinceFirst != null) trend = sinceFirst >= 5 ? "up" : sinceFirst <= -5 ? "down" : "flat";
  return { latest, previous, first, best, deltaW, sinceFirst, trend, count: sessions.length };
}
