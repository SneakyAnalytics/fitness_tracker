// Chart data and wording for the Performance Manager (CTL / ATL / TSB, past and projected).

/** One row per day: solid values for the past, `...P` values for the projection (joined at the last real day). */
export function projectionData(lp) {
  if (!lp?.history?.length) return [];
  const last = lp.history[lp.history.length - 1];
  const past = lp.history.map((r) => ({ date: r.date, ctl: r.ctl, atl: r.atl, tsb: r.tsb }));
  past[past.length - 1] = { ...past[past.length - 1], ctlP: last.ctl, atlP: last.atl, tsbP: last.tsb };
  const ahead = (lp.projection || []).map((r) => ({ date: r.date, ctlP: r.ctl, atlP: r.atl, tsbP: r.tsb, kind: r.kind, tss: r.tss }));
  return [...past, ...ahead];
}

/** How form reads: TSB is fitness minus fatigue going into the day. */
export function formLabel(tsb) {
  if (tsb == null) return "";
  if (tsb >= 15) return "very fresh (may be detraining)";
  if (tsb >= 5) return "fresh";
  if (tsb > -10) return "balanced";
  if (tsb > -30) return "building";
  return "deep fatigue";
}

/** Projected form on a given date, or null if the date is outside the projection. */
export function formOn(lp, dateStr) {
  const row = (lp?.projection || []).find((r) => r.date === dateStr);
  return row ? { tsb: Math.round(row.tsb), ctl: Math.round(row.ctl), kind: row.kind } : null;
}

/** The lowest projected form in the window and the day it happens. */
export function lowestForm(lp) {
  const rows = lp?.projection || [];
  if (!rows.length) return null;
  const low = rows.reduce((a, b) => (b.tsb < a.tsb ? b : a));
  return { date: low.date, tsb: Math.round(low.tsb) };
}

export function plannedDayCount(lp) {
  return (lp?.projection || []).filter((r) => r.kind === "planned").length;
}
