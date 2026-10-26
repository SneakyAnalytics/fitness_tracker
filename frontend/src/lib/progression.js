/** Units a key-session trend can be shown in. */
export const MODES = { watts: { unit: "W", label: "Watts", trendMin: 5 }, ftp: { unit: "%", label: "% of FTP", trendMin: 1.5 } };

/**
 * Sessions (oldest first) as chart rows in the chosen unit: `value` is what was ridden, `plan` what the plan asked for.
 * In % of FTP mode each session is measured against the FTP it was prescribed against, so a changed FTP
 * doesn't masquerade as progress or regression.
 */
export function progressionRows(sessions, mode = "watts") {
  return (sessions || [])
    .map((s) => {
      if (mode === "ftp") {
        const value = s.pct_ftp != null ? Math.round(s.pct_ftp * 1000) / 10 : null;
        const plan = s.work_target_power != null && s.ftp ? Math.round((s.work_target_power / s.ftp) * 1000) / 10 : null;
        return { ...s, value, plan };
      }
      return { ...s, value: s.work_avg_power, plan: s.work_target_power ?? null };
    })
    .filter((r) => r.value != null);
}

/** Latest vs previous, best, and direction for a run of sessions in one unit. */
export function summarizeProgression(sessions, mode = "watts") {
  const rows = progressionRows(sessions, mode);
  if (!rows.length) return null;
  const latest = rows[rows.length - 1];
  const previous = rows.length > 1 ? rows[rows.length - 2] : null;
  const first = rows[0];
  const best = rows.reduce((a, b) => (b.value > a.value ? b : a));
  const round = (n) => (mode === "ftp" ? Math.round(n * 10) / 10 : Math.round(n));
  const delta = previous ? round(latest.value - previous.value) : null;
  const sinceFirst = rows.length > 1 ? round(latest.value - first.value) : null;
  const vsPlan = latest.plan != null ? round(latest.value - latest.plan) : null;
  let trend = "new";
  if (sinceFirst != null) trend = sinceFirst >= MODES[mode].trendMin ? "up" : sinceFirst <= -MODES[mode].trendMin ? "down" : "flat";
  return { rows, latest, previous, first, best, delta, sinceFirst, vsPlan, trend, count: rows.length, mode };
}

/**
 * One line comparing a ride's work intervals with the plan, from the intervals endpoint's `work` summary:
 * { text, tone: "good" | "warn" | "plain" } or null. Within 3% of the plan counts as on plan.
 */
export function workVsPlan(work, planFtp) {
  if (!work?.avg_power) return null;
  const rode = Math.round(work.avg_power);
  if (!work.target_power) return { tone: "plain", text: `Work intervals averaged ${rode} W.` };
  const plan = Math.round(work.target_power);
  const diff = Math.round(work.diff_w);
  const pct = Math.abs(work.diff_pct);
  if (pct <= 3) return { tone: "good", text: `Work intervals averaged ${rode} W against ${plan} W planned: on plan.` };
  const way = diff < 0 ? "under" : "over";
  const hint = diff < 0 && planFtp ? ` The plan assumed an FTP of ${planFtp} W; if Zwift's FTP was lower, that alone lowers every ERG target.` : "";
  return { tone: "warn", text: `Work intervals averaged ${rode} W against ${plan} W planned: ${Math.abs(diff)} W ${way} (${pct}%).${hint}` };
}
