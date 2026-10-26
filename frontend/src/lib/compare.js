// Pure helpers for the Compare page: pairing two rides, merging their series, and the summary deltas.

const norm = (s) => (s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

/** Default pair: the newest ride and the previous ride with the same name (else simply the previous ride). */
export function defaultPair(rides) {
  if (!rides?.length) return [null, null];
  const [first, ...rest] = rides;
  const same = rest.find((r) => norm(r.name) === norm(first.name));
  return [first.id, (same || rest[0] || {}).id ?? null];
}

/** The ride to compare `id` with: the previous ride of the same name, else the one before it in the list. */
export function similarTo(rides, id) {
  const i = (rides || []).findIndex((r) => String(r.id) === String(id));
  if (i < 0) return null;
  const older = rides.slice(i + 1);
  const same = older.find((r) => norm(r.name) === norm(rides[i].name));
  return (same || older[0] || rides.find((r) => r !== rides[i]) || {}).id ?? null;
}

/** Rows of { min, a, b, aHr, bHr } on a shared time axis (each ride keeps its own step). */
export function mergeSeries(a, b) {
  const stepMin = (ride) => (ride ? ride.step_sec / 60 : 0);
  const rows = new Map();
  const add = (ride, key, field) => {
    if (!ride) return;
    ride[key].forEach((v, i) => {
      const min = Math.round(i * stepMin(ride) * 100) / 100;
      const row = rows.get(min) || { min };
      row[field] = v;
      rows.set(min, row);
    });
  };
  add(a, "power", "a");
  add(b, "power", "b");
  add(a, "hr", "aHr");
  add(b, "hr", "bHr");
  return [...rows.values()].sort((x, y) => x.min - y.min);
}

const FIELDS = [
  { key: "avg_power", label: "Average power", unit: "W" },
  { key: "np", label: "Normalized power", unit: "W" },
  { key: "intensity_factor", label: "Intensity factor", unit: "" },
  { key: "tss", label: "TSS", unit: "" },
  { key: "avg_hr", label: "Average heart rate", unit: "bpm" },
  { key: "max_hr", label: "Max heart rate", unit: "bpm" },
];

/** Summary rows with B minus A (A is the ride being compared against B). */
export function summaryRows(a, b) {
  const rows = [{ label: "Duration", unit: "min", a: a && Math.round(a.duration_sec / 60), b: b && Math.round(b.duration_sec / 60) }];
  FIELDS.forEach((f) => rows.push({ label: f.label, unit: f.unit, a: a?.summary?.[f.key] ?? null, b: b?.summary?.[f.key] ?? null }));
  return rows
    .filter((r) => r.a != null || r.b != null)
    .map((r) => ({ ...r, delta: r.a != null && r.b != null ? Math.round((r.a - r.b) * 100) / 100 : null }));
}

/** Interval pairs by position: how the same prescribed block went each time. */
export function intervalRows(a, b) {
  const ia = a?.intervals || [];
  const ib = b?.intervals || [];
  const n = Math.max(ia.length, ib.length);
  return Array.from({ length: n }, (_, i) => ({ index: i + 1, name: ia[i]?.name || ib[i]?.name, a: ia[i] || null, b: ib[i] || null }));
}
