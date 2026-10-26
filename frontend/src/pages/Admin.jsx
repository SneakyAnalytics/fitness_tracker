import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addDays, format, parseISO, startOfWeek, subWeeks } from "date-fns";
import { AlertTriangle, Check, Info, Plus, Trash2 } from "lucide-react";
import { adminAPI, zwiftAPI } from "../api/client";
import { CoachAdmin } from "../components/CoachLogo";
import "../styles/pages.css";
import "./Admin.css";

const iso = (d) => format(d, "yyyy-MM-dd");
const errorText = (e) => e?.response?.data?.detail || e?.message || "Something went wrong";

function Problems() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["admin", "events"], queryFn: () => adminAPI.events().then((r) => r.data.events), refetchInterval: 60000 });
  const dismiss = useMutation({
    mutationFn: (ids) => adminAPI.dismissEvents(ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "events"] }),
  });
  const events = data || [];
  return (
    <section className="card admin-section">
      <div className="admin-section-head">
        <h2>Problems and updates</h2>
        {events.length > 0 && (
          <button className="btn btn-outline" onClick={() => dismiss.mutate(events.map((e) => e.id))}>Dismiss all</button>
        )}
      </div>
      {events.length === 0 ? (
        <p className="admin-empty"><Check size={16} /> Nothing needs attention.</p>
      ) : (
        <ul className="event-list">
          {events.map((e) => (
            <li key={e.id} className={`event ${e.level}`}>
              {e.level === "info" ? <Info size={16} /> : <AlertTriangle size={16} />}
              <div>
                <div>{e.message}</div>
                <small>{e.created_at} · {e.source}</small>
              </div>
              <button className="btn btn-outline" onClick={() => dismiss.mutate([e.id])} aria-label="Dismiss">Dismiss</button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RideFileChanger({ workout, onDone }) {
  const { data: files } = useQuery({
    queryKey: ["admin", "fit-files", workout.workout_date],
    queryFn: () => adminAPI.fitFiles(workout.workout_date).then((r) => r.data.fit_files),
  });
  const [choice, setChoice] = useState(workout.fit_file_id ?? "");
  const save = useMutation({
    mutationFn: () => adminAPI.assignFit(workout.id, choice === "" ? null : Number(choice)),
    onSuccess: onDone,
  });
  const label = (f) => `${f.filename} · ${f.tss ?? "?"} TSS · ${f.duration ?? "?"} h`;
  return (
    <div className="inline-editor">
      <select className="input" value={choice} onChange={(e) => setChoice(e.target.value)}>
        <option value="">No ride file</option>
        {(files || []).map((f) => <option key={f.id} value={f.id}>{label(f)}</option>)}
      </select>
      <button className="btn btn-primary" disabled={save.isPending || String(workout.fit_file_id ?? "") === String(choice)} onClick={() => save.mutate()}>Save</button>
      <button className="btn btn-outline" onClick={onDone}>Cancel</button>
      {save.isError && <span className="admin-error">{errorText(save.error)}</span>}
    </div>
  );
}

function Workouts() {
  const qc = useQueryClient();
  const [start, setStart] = useState(iso(subWeeks(startOfWeek(new Date(), { weekStartsOn: 1 }), 1)));
  const [end, setEnd] = useState(iso(addDays(startOfWeek(new Date(), { weekStartsOn: 1 }), 6)));
  const [editing, setEditing] = useState(null);
  const [confirming, setConfirming] = useState(null);
  const key = ["admin", "workouts", start, end];
  const { data, isLoading } = useQuery({ queryKey: key, queryFn: () => adminAPI.workouts(start, end).then((r) => r.data.workouts) });
  const refresh = () => {
    setEditing(null);
    setConfirming(null);
    // ride links and deletions change the calendar, dashboard and review too
    qc.invalidateQueries();
  };
  const remove = useMutation({ mutationFn: (id) => adminAPI.deleteWorkout(id), onSuccess: refresh });
  return (
    <section className="card admin-section">
      <div className="admin-section-head">
        <h2>Workouts and ride files</h2>
        <div className="range">
          <input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} aria-label="From" />
          <span>to</span>
          <input className="input" type="date" value={end} onChange={(e) => setEnd(e.target.value)} aria-label="To" />
        </div>
      </div>
      {isLoading && <p className="admin-empty">Loading…</p>}
      {data && data.length === 0 && <p className="admin-empty">No workouts in this range.</p>}
      {data && data.length > 0 && (
        <div className="table-scroll">
          <table className="admin-table">
            <thead>
              <tr><th>Date</th><th>Workout</th><th>TrainingPeaks</th><th>Ride file</th><th /></tr>
            </thead>
            <tbody>
              {data.map((w) => (
                <tr key={w.id}>
                  <td>{format(parseISO(w.workout_date), "EEE MMM d")}</td>
                  <td>{w.title}</td>
                  <td>{w.workout_tss ?? "–"} TSS · {w.workout_duration ?? "–"} h</td>
                  <td>
                    {editing === w.id ? (
                      <RideFileChanger workout={w} onDone={refresh} />
                    ) : w.fit_filename ? (
                      <span>{w.fit_filename}<small> · {w.fit_tss ?? "?"} TSS</small></span>
                    ) : <span className="muted">none</span>}
                  </td>
                  <td className="row-actions">
                    {confirming === w.id ? (
                      <>
                        <button className="btn btn-danger" disabled={remove.isPending} onClick={() => remove.mutate(w.id)}>Delete for good</button>
                        <button className="btn btn-outline" onClick={() => setConfirming(null)}>Keep</button>
                      </>
                    ) : (
                      <>
                        <button className="btn btn-outline" onClick={() => setEditing(editing === w.id ? null : w.id)}>Ride file</button>
                        <button className="btn btn-outline" aria-label={`Delete ${w.title}`} onClick={() => setConfirming(w.id)}><Trash2 size={14} /></button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {remove.isError && <p className="admin-error">{errorText(remove.error)}</p>}
    </section>
  );
}

const CATEGORIES = ["event", "performance", "fitness", "health", "other"];
const STATUSES = ["active", "completed", "paused", "abandoned"];

function Goals() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["admin", "goals"], queryFn: () => adminAPI.goals().then((r) => r.data.goals) });
  const blank = { description: "", category: "event", priority: 3, target_date: "" };
  const [draft, setDraft] = useState(blank);
  const done = () => {
    qc.invalidateQueries({ queryKey: ["admin", "goals"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  };
  const add = useMutation({
    mutationFn: () => adminAPI.addGoal({ ...draft, priority: Number(draft.priority), target_date: draft.target_date || null }),
    onSuccess: () => { setDraft(blank); done(); },
  });
  const update = useMutation({ mutationFn: ({ id, patch }) => adminAPI.updateGoal(id, patch), onSuccess: done });
  return (
    <section className="card admin-section">
      <div className="admin-section-head"><h2>Goals</h2></div>
      <form className="goal-form" onSubmit={(e) => { e.preventDefault(); if (draft.description.trim()) add.mutate(); }}>
        <input className="input grow" placeholder="New goal or event" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
        <select className="input" value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })} aria-label="Category">
          {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
        </select>
        <select className="input" value={draft.priority} onChange={(e) => setDraft({ ...draft, priority: e.target.value })} aria-label="Priority">
          {[1, 2, 3, 4, 5].map((p) => <option key={p} value={p}>Priority {p}</option>)}
        </select>
        <input className="input" type="date" value={draft.target_date} onChange={(e) => setDraft({ ...draft, target_date: e.target.value })} aria-label="Target date" />
        <button className="btn btn-primary" type="submit" disabled={add.isPending}><Plus size={14} /> Add</button>
      </form>
      {add.isError && <p className="admin-error">{errorText(add.error)}</p>}
      {update.isError && <p className="admin-error">{errorText(update.error)}</p>}
      <div className="table-scroll">
        <table className="admin-table">
          <thead><tr><th>Goal</th><th>Target</th><th>Priority</th><th>Status</th></tr></thead>
          <tbody>
            {(data || []).map((g) => (
              <tr key={g.id} className={g.status === "active" ? "" : "inactive"}>
                <td>{g.description}</td>
                <td>
                  <input className="input" type="date" value={g.target_date || ""} onChange={(e) => e.target.value && update.mutate({ id: g.id, patch: { target_date: e.target.value } })} aria-label={`Target date for ${g.description}`} />
                  {g.days_until != null && g.status === "active" && <small> {g.days_until >= 0 ? `${g.days_until} d` : `${-g.days_until} d ago`}</small>}
                </td>
                <td>
                  <select className="input" value={g.priority} onChange={(e) => update.mutate({ id: g.id, patch: { priority: Number(e.target.value) } })} aria-label={`Priority for ${g.description}`}>
                    {[1, 2, 3, 4, 5].map((p) => <option key={p}>{p}</option>)}
                  </select>
                </td>
                <td>
                  <select className="input" value={g.status} onChange={(e) => update.mutate({ id: g.id, patch: { status: e.target.value } })} aria-label={`Status for ${g.description}`}>
                    {STATUSES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ZwiftFiles() {
  const [weekStart, setWeekStart] = useState(iso(startOfWeek(new Date(), { weekStartsOn: 1 })));
  const run = useMutation({
    mutationFn: () => zwiftAPI.generateWorkouts(weekStart, iso(addDays(parseISO(weekStart), 6))).then((r) => r.data),
  });
  return (
    <section className="card admin-section">
      <div className="admin-section-head"><h2>Zwift workout files</h2></div>
      <p className="admin-note">Rebuilds the .zwo files for a week from its saved plan, for example after editing a plan or changing FTP.</p>
      <div className="range">
        <label>Week starting <input className="input" type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} /></label>
        <button className="btn btn-primary" disabled={run.isPending} onClick={() => run.mutate()}>{run.isPending ? "Generating…" : "Regenerate files"}</button>
      </div>
      {run.isSuccess && <p className="admin-ok"><Check size={16} /> {run.data.message}</p>}
      {run.isError && <p className="admin-error">{errorText(run.error)}</p>}
    </section>
  );
}

function Admin() {
  return (
    <div className="page-container admin-page">
      <div className="page-header">
        <div className="hero-title">
          <CoachAdmin size={96} />
          <div>
            <h1 className="page-title">Admin</h1>
            <p className="header-subtitle">Problems, ride files, goals and Zwift files. Imports and matching happen in Weekly Coaching.</p>
          </div>
        </div>
      </div>
      <Problems />
      <Workouts />
      <Goals />
      <ZwiftFiles />
    </div>
  );
}

export default Admin;
