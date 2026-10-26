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
