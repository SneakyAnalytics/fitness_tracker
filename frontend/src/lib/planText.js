import { addDays, format, parseISO } from "date-fns";
import { flattenExercises, parseJSONField, resolvePowerTarget } from "./workouts";

/** "Focus" and "considerations" from the weekly plan's notes (stored as JSON text, sometimes plain text). */
export function planNotes(plan) {
  const parsed = parseJSONField(plan?.notes, null);
  if (parsed && typeof parsed === "object") return { focus: parsed.weekFocus || "", considerations: parsed.specialConsiderations || "" };
  return { focus: typeof plan?.notes === "string" ? plan.notes : "", considerations: "" };
}

const clock = (sec) => `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`;
const SKIP = /(warm|cool|recover|rest|easy spin|flush|spin-?up|opener)/i;

/** The sustained hard parts of a ride, one short line each: ["15:00 @ 277-293W", ...]. */
export function intervalLines(intervals, ftp) {
  return (intervals || [])
    .filter((iv) => (iv.duration || 0) >= 240 && !SKIP.test(iv.name || ""))
    .map((iv) => {
      const t = resolvePowerTarget(iv.powerTarget, ftp);
      return `${clock(iv.duration)}${t ? ` @ ${t.label}` : ""}`;
    });
}

/** One session as plain text lines (no leading dash). */
export function sessionLine(w) {
  const parts = [w.name, w.type, w.plannedDuration ? `${w.plannedDuration} min` : null,
    w.plannedTSS_max ? `${w.plannedTSS_min}-${w.plannedTSS_max} TSS` : null].filter(Boolean);
  return parts.join(" · ");
}

export function sessionDetail(w, ftp) {
  const bike = intervalLines(parseJSONField(w.intervals, []), ftp);
  if (bike.length) return bike.join("  |  ");
  const moves = flattenExercises(w).map((e) => e.name).filter(Boolean);
  if (moves.length) return `${moves.length} movements: ${moves.slice(0, 6).join(", ")}${moves.length > 6 ? ", ..." : ""}`;
  return "";
}

/** Group sessions by date, in order, as [{ date, label, sessions }] covering all seven days. */
export function groupByDay(workouts, weekStart) {
  const start = typeof weekStart === "string" ? parseISO(weekStart) : weekStart;
  return Array.from({ length: 7 }, (_, i) => {
    const d = addDays(start, i);
    const key = format(d, "yyyy-MM-dd");
    return { date: key, label: format(d, "EEE MMM d"), sessions: workouts.filter((w) => (w.date || "").slice(0, 10) === key) };
  });
}

/** The whole week as text you can paste into a message. */
export function planAsText({ weekStart, plan, workouts, ftp }) {
  const start = typeof weekStart === "string" ? parseISO(weekStart) : weekStart;
  const notes = planNotes(plan);
  const lines = [
    `Week of ${format(start, "MMM d")} to ${format(addDays(start, 6), "MMM d, yyyy")}` +
      (plan?.plannedTSS_min ? ` · plan ${plan.plannedTSS_min}-${plan.plannedTSS_max} TSS` : "") + (ftp ? ` · FTP ${ftp} W` : ""),
  ];
  if (notes.focus) lines.push(`Focus: ${notes.focus}`);
  for (const day of groupByDay(workouts, start)) {
    lines.push("", day.label);
    if (!day.sessions.length) lines.push("  Rest");
    for (const w of day.sessions) {
      lines.push(`  - ${sessionLine(w)}`);
      const detail = sessionDetail(w, ftp);
      if (detail) lines.push(`      ${detail}`);
    }
  }
  return lines.join("\n");
}
