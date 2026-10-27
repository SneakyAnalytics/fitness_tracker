// Pure helpers for Gym mode: turning an exercise's prescription into a list of sets to tick off.

export const DEFAULT_REST_SECONDS = 60;

/** One entry per set to perform: the set definitions repeat `sets` times each ("3 x 10" is one definition). */
export function expandSets(exercise) {
  const defs = Array.isArray(exercise?.sets) ? exercise.sets : [];
  const out = [];
  defs.forEach((def) => {
    const count = Math.max(1, Number(def.sets) || 1);
    for (let i = 0; i < count; i += 1) out.push(def);
  });
  return out.length ? out : [{}]; // an exercise with no set detail is still one thing to do
}

/** Seconds to rest after a set: the exercise's own number if it gives one, else a sensible default. */
export function restSeconds(exercise, fallback = DEFAULT_REST_SECONDS) {
  const defs = Array.isArray(exercise?.sets) ? exercise.sets : [];
  const given = defs.map((d) => Number(d.restBetweenSets) || Number(d.restTime) || 0).find((n) => n > 0);
  return given ? Math.min(given, 600) : fallback;
}

export const clock = (seconds) => {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

/** 0-1 progress through the whole session, counting sets: done is the completed count per exercise index. */
export function sessionProgress(exercises, done) {
  const total = exercises.reduce((n, e) => n + expandSets(e).length, 0);
  if (!total) return 0;
  const finished = exercises.reduce((n, e, i) => n + Math.min(done[i] || 0, expandSets(e).length), 0);
  return finished / total;
}

/** The top of the prescribed rep range as a number ("8-10" -> 10), or null for timed work such as "30 sec". */
export function targetRepsTop(setDef) {
  const raw = setDef?.reps ?? setDef?.targetReps;
  if (raw == null || /sec|min|\bs\b/i.test(String(raw))) return null;
  const nums = String(raw).match(/\d+/g);
  return nums ? Math.max(...nums.map(Number)) : null;
}

const roundTo = (n, step) => Math.round(n / step) * step;

/**
 * Next weight from last time's sets: if every set at the top weight reached the top of the rep range, add ~5%
 * (at least 2.5 lb, rounded to 2.5); otherwise hold. Returns null when there is nothing to build on.
 */
export function suggestWeight(last, targetTop) {
  const sets = (last?.sets || []).filter((s) => s.weight != null);
  if (!sets.length) return null;
  const top = Math.max(...sets.map((s) => s.weight));
  // An older log with one number for the whole exercise ("24" for 3 x 8) can't show whether each set hit the target.
  if (sets.some((s) => s.total)) return { weight: top, change: "hold", reason: `repeat ${top} lb (the last log has total reps, not reps per set)` };
  const atTop = sets.filter((s) => s.weight === top);
  const reached = targetTop != null && atTop.every((s) => s.reps != null && s.reps >= targetTop);
  if (!reached) return { weight: top, change: "hold", reason: targetTop ? `hold at ${top} lb until every set reaches ${targetTop} reps` : `repeat ${top} lb` };
  const weight = roundTo(top + Math.max(2.5, top * 0.05), 2.5);
  return { weight, change: "up", reason: `every set hit ${targetTop} reps at ${top} lb, so go up` };
}

/** "45 lb × 10, 10, 8" for a logged session. */
export function describeSession(session) {
  if (!session) return "";
  const weights = [...new Set(session.sets.filter((s) => s.weight != null).map((s) => s.weight))].sort((a, b) => a - b);
  const reps = session.sets.filter((s) => s.reps != null).map((s) => s.reps).join(", ") + (session.sets.some((s) => s.total) ? " total" : "");
  const weight = weights.length ? `${weights.join("/")} lb` : "bodyweight";
  return reps ? `${weight} × ${reps}` : weight;
}

/** The cues for one set (the plan writes them per set) plus the exercise's own, without repeats. */
export function cuesFor(exercise, setIndex) {
  const sets = expandSets(exercise);
  const def = sets[Math.min(setIndex, sets.length - 1)] || {};
  const list = (v) => (Array.isArray(v) ? v : v ? [v] : []);
  return [...new Set([...list(def.notes), ...list(def.cues), ...list(exercise?.cues)])];
}

/** What gets saved for an exercise: only the sets that were ticked, in the shape the API and strength log read. */
export function logEntry(exercise, sets) {
  const done = sets.filter((s) => s && (s.weight || s.reps));
  if (!done.length) return null;
  const weights = done.map((s) => Number(s.weight)).filter((n) => Number.isFinite(n) && n > 0);
  return {
    name: exercise.name,
    sets: done.map((s) => ({ weight: s.weight || "", reps: s.reps || "" })),
    reps: done.map((s) => s.reps).filter(Boolean).join(", "),
    weight: weights.length ? String(Math.max(...weights)) : "",
    notes: "",
  };
}

/** A message a person can act on, instead of axios' "Network Error". */
export function saveErrorMessage(err) {
  if (!err?.response) return "Can't reach the server. Check that Tailscale is connected. Your numbers are kept and will retry.";
  const detail = err.response.data?.detail;
  return `The server refused the save (${err.response.status}${detail ? `: ${typeof detail === "string" ? detail : "invalid data"}` : ""}).`;
}
