// Pure helpers for workout data (kept separate so they can be unit tested).

export function parseJSONField(value, fallback = []) {
  if (value == null || value === "") return fallback;
  if (typeof value !== "string") return value;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

// Mirrors src/utils/erg_execution.resolve_target on the backend.
export function resolvePowerTarget(target, ftp) {
  if (!target) return null;
  const toWatts = (value, unit) =>
    unit === "percent_ftp" ? (Number(value) / 100) * ftp : Number(value);

  if (target.type === "range") {
    const unit = target.unit || "watts";
    const lo = toWatts(target.min, unit);
    const hi = toWatts(target.max, unit);
    return { low: Math.min(lo, hi), high: Math.max(lo, hi), label: `${Math.round(Math.min(lo, hi))}-${Math.round(Math.max(lo, hi))}W` };
  }
  if (target.start && target.end) {
    const s = toWatts(target.start.value, target.start.type);
    const e = toWatts(target.end.value, target.end.type);
    return { low: s, high: e, label: `${Math.round(s)}→${Math.round(e)}W ramp` };
  }
  if (target.type === "percent_ftp") {
    const w = toWatts(target.value, "percent_ftp");
    return { low: w, high: w, label: `${target.value}% FTP (${Math.round(w)}W)` };
  }
  if (target.value != null) {
    const w = Number(target.value);
    return { low: w, high: w, label: `${Math.round(w)}W` };
  }
  return null;
}

export function exerciseLookupUrl(name) {
  // encodeURIComponent keeps names like "Bird Dog / Dead Bug" intact.
  const q = encodeURIComponent(`${name} exercise demonstration`);
  return `https://www.google.com/search?q=${q}&tbm=isch`;
}

// One list per day: completed workouts (carrying their matched plan) first,
// then planned workouts nobody has matched yet.
export function mergeDayWorkouts(proposed, completed, dateStr) {
  const onDay = (w) => (w.date || "").startsWith(dateStr);
  const dayPlanned = proposed.filter(onDay);
  const dayDone = completed.filter(onDay);
  // A confirmed match wins; otherwise use the review step's suggestion.
  const planIdOf = (c) => c.proposed_workout_id || c.suggested_proposed_workout_id || null;
  const matchedIds = new Set(dayDone.map(planIdOf).filter(Boolean));
  const plansById = new Map(proposed.map((p) => [p.id, p]));

  return [
    ...dayDone.map((c) => {
      const plan = planIdOf(c) ? plansById.get(planIdOf(c)) : null;
      return {
        ...(plan || {}),
        ...c,
        key: `done-${c.id}`,
        completed: true,
        plan,
        unconfirmed: !c.proposed_workout_id && !c.proposed_workout_name,
        proposed_workout_name: c.proposed_workout_name || c.suggested_label || null,
        name: c.title,
        actualDuration: c.metrics?.actual_duration ?? null,
        actualTSS: c.metrics?.actual_tss ?? null,
      };
    }),
    ...dayPlanned
      .filter((p) => !matchedIds.has(p.id))
      .map((p) => ({ ...p, key: `plan-${p.id}`, completed: false })),
  ];
}

export function isRoutineType(type) {
  const t = (type || "").toLowerCase();
  return ["strength", "routine", "yoga", "mobility"].some((k) => t.includes(k));
}

export function isCardioType(type) {
  const t = (type || "").toLowerCase();
  return ["bike", "run", "cycling"].some((k) => t.includes(k));
}

export function flattenExercises(workout) {
  const sections = parseJSONField(workout.sections, []);
  let exercises = parseJSONField(workout.exercises, []);
  if (Array.isArray(sections)) {
    sections.forEach((section) => {
      if (Array.isArray(section.exercises)) {
        exercises = [...exercises, ...section.exercises.map((ex) => ({ ...ex, section: section.name }))];
      }
    });
  }
  return Array.isArray(exercises) ? exercises : [];
}

// Seconds to time for one movement/side, or null for rep-based work.
// Uses structured fields first, then text like "30-40 seconds each side" or "1 min".
export function movementTiming(exercise) {
  const sets = Array.isArray(exercise.sets) ? exercise.sets : [];
  const first = sets.find((s) => s.duration || s.workTime || s.reps || s.targetReps) || {};
  const text = [first.reps, first.targetReps, exercise.name]
    .filter((v) => typeof v === "string")
    .join(" ")
    .toLowerCase();
  const perSide = Boolean(first.perSide) || /each (side|leg|arm)|per (side|leg|arm)/.test(text);

  let seconds = Number(first.duration) || Number(first.workTime) || null;
  if (!seconds) {
    const m = text.match(/(\d+)(?:\s*-\s*(\d+))?\s*(seconds?|secs?|s\b|minutes?|mins?|min\b)/);
    if (m) {
      const value = Number(m[2] || m[1]); // use the top of a range, e.g. 30-40s -> 40s
      seconds = /^m/.test(m[3]) ? value * 60 : value;
    }
  }
  if (!seconds || seconds < 5 || seconds > 1800) return null;
  return { seconds, perSide };
}
