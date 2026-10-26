import { isWet } from "./weather";

const planIdOf = (c) => c.proposed_workout_id || c.suggested_proposed_workout_id || null;

/** Where a week stands: load against the plan's band, sessions done and missed, and rain still to come. */
export function summarizeWeek({ proposed = [], completed = [], plan = null, weather = {}, today }) {
  const planIds = new Set(proposed.map((p) => p.id));
  const matched = new Set(completed.map(planIdOf).filter((id) => planIds.has(id)));
  // a zero-minute "Rest Day" entry is a day off, not a session to do or miss
  const sessions = proposed.filter((p) => (p.plannedDuration ?? 1) > 0);
  const unmatched = sessions.filter((p) => !matched.has(p.id));
  const tss = completed.reduce((sum, c) => sum + (Number(c.metrics?.actual_tss) || 0), 0);
  const band = plan?.plannedTSS_min ? { min: plan.plannedTSS_min, max: plan.plannedTSS_max || plan.plannedTSS_min } : null;
  return {
    tss: Math.round(tss),
    band,
    planned: sessions.length,
    matched: sessions.filter((p) => matched.has(p.id)).length,
    unplanned: completed.filter((c) => !planIdOf(c) || !planIds.has(planIdOf(c))).length,
    missed: unmatched.filter((p) => (p.date || "").slice(0, 10) < today).length,
    upcoming: unmatched.filter((p) => (p.date || "").slice(0, 10) >= today).length,
    wetDays: Object.entries(weather).filter(([d, w]) => d >= today && isWet(w)).map(([d]) => d).sort(),
  };
}

/** The review step's rows (status: confirmed | suggested | none) as a summary for the coaching header. */
export function summarizeReview(rows = []) {
  const confirmed = rows.filter((r) => r.status === "confirmed").length;
  const toConfirm = rows.filter((r) => r.status === "suggested").length;
  const minutes = rows.reduce((sum, r) => sum + (Number(r.minutes) || 0), 0);
  const tss = rows.reduce((sum, r) => sum + (Number(r.tss) || 0), 0);
  return { total: rows.length, confirmed, toConfirm, other: rows.length - confirmed - toConfirm, hours: Math.round(minutes / 6) / 10, tss: Math.round(tss) };
}
