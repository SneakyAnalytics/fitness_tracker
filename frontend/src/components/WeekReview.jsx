import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { Check, CheckCircle2, Loader2, Pencil, RefreshCw, Upload } from "lucide-react";
import apiClient from "../api/client";
import "./WeekReview.css";

const day = (d) => format(parseISO(d), "EEE MMM d");

function MatchPicker({ row, planned, categories, onSave, onCancel }) {
  const sameDayFirst = [...planned].sort((a, b) => (a.date === row.date ? -1 : 0) - (b.date === row.date ? -1 : 0));
  const current = row.match?.proposed_workout_id ? `plan:${row.match.proposed_workout_id}` : `label:${row.match?.name || ""}`;
  const [choice, setChoice] = useState(current);
  const [custom, setCustom] = useState("");
  const save = () => {
    if (choice === "custom") onSave({ label: custom });
    else if (choice.startsWith("plan:")) onSave({ proposed_workout_id: Number(choice.slice(5)) });
    else onSave({ label: choice.slice(6) });
  };
  return (
    <div className="match-picker">
      <select className="input" value={choice} onChange={(e) => setChoice(e.target.value)}>
        <optgroup label="Planned this week">
          {sameDayFirst.map((p) => (
            <option key={p.id} value={`plan:${p.id}`}>
              {format(parseISO(p.date), "EEE")} · {p.name}
              {p.done ? " (already matched)" : ""}
            </option>
          ))}
        </optgroup>
        <optgroup label="Not part of the plan">
          {categories.map((c) => (
            <option key={c} value={`label:${c}`}>
              {c}
            </option>
          ))}
          <option value="custom">Something else…</option>
        </optgroup>
      </select>
      {choice === "custom" && (
        <input className="input" autoFocus value={custom} placeholder="e.g. Ride with friends"
               onChange={(e) => setCustom(e.target.value)} />
      )}
      <div className="match-picker-actions">
        <button className="btn btn-primary btn-sm" onClick={save} disabled={choice === "custom" && !custom.trim()}>
          Save
        </button>
        <button className="btn btn-outline btn-sm" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function AnalysisNote({ row }) {
  const a = row.analysis;
  if (a?.state === "queued" || a?.state === "running")
    return <span className="analysis-note"><Loader2 size={12} className="spin" /> analyzing…</span>;
  if (a?.state === "error") return <span className="analysis-note error">analysis failed</span>;
  const score = a?.execution_score ?? row.execution_score;
  return score != null ? <span className="analysis-note">execution {score}/10</span> : null;
}

function Row({ row, planned, categories, onMatch }) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const m = row.match || {};
  const confirmed = row.status === "confirmed";
  const save = async (body) => {
    setBusy(true);
    try {
      await onMatch({ workout_id: row.id, ...body });
      setEditing(false);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className={`review-row ${confirmed ? "confirmed" : "pending"}`}>
      <div className="review-workout">
        <span className="review-title">{row.title}</span>
        <span className="review-meta">
          {row.type} · {row.minutes} min{row.tss ? ` · ${Math.round(row.tss)} TSS` : ""}
        </span>
      </div>
      {editing ? (
        <MatchPicker row={row} planned={planned} categories={categories} onSave={save}
                     onCancel={() => setEditing(false)} />
      ) : (
        <div className="review-match">
          {confirmed ? (
            <span className={`match-pill ${m.kind}`}>
              <CheckCircle2 size={14} /> {m.name}
            </span>
          ) : m.name ? (
            <span className={`match-pill suggested ${m.kind}`} title={`${m.confidence} confidence`}>
              {m.kind === "plan" ? "→ " : ""}
              {m.name}
            </span>
          ) : (
            <span className="match-pill unknown">What was this?</span>
          )}
          <AnalysisNote row={row} />
          <span className="review-actions">
            {!confirmed && m.name && (
              <button className="icon-action confirm" disabled={busy} aria-label={`Confirm ${m.name}`}
                      onClick={() => save(m.kind === "plan" ? { proposed_workout_id: m.proposed_workout_id } : { label: m.name })}>
                <Check size={18} />
              </button>
            )}
            <button className="icon-action" onClick={() => setEditing(true)} aria-label="Change match">
              <Pencil size={16} />
            </button>
          </span>
        </div>
      )}
    </div>
  );
}

function WeekReview({ weekStart, onDone }) {
  const queryClient = useQueryClient();
  const fileRef = useRef(null);
  const [uploadMsg, setUploadMsg] = useState("");
  const key = ["review", weekStart];
  const { data, isLoading, error } = useQuery({
    queryKey: key,
    queryFn: async () => (await apiClient.get("/review/week", { params: { week_start: weekStart } })).data,
    // Keep polling while a sync or analysis is in flight.
    refetchInterval: (q) => {
      const d = q.state.data;
      const busy = d?.sync?.state === "running" ||
        d?.workouts?.some((w) => ["queued", "running"].includes(w.analysis?.state));
      return busy ? 3000 : false;
    },
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: key });

  const match = async (body) => {
    await apiClient.post("/review/match", body);
    await refresh();
  };
  const confirmAll = async () => {
    await apiClient.post("/review/confirm-all", { week_start: weekStart });
    await refresh();
  };
  const sync = async () => {
    await apiClient.post("/review/sync", { week_start: weekStart });
    await refresh();
  };
  const upload = async (files) => {
    let done = 0;
    for (const file of files) {
      const name = file.name.toLowerCase();
      const path = name.endsWith(".csv") ? (name.includes("metric") ? "/upload/metrics" : "/upload/workouts") : "/upload/fit";
      const form = new FormData();
      form.append("file", file);
      setUploadMsg(`Uploading ${file.name}…`);
      await apiClient.post(path, form, { headers: { "Content-Type": "multipart/form-data" }, timeout: 120000 });
      done += 1;
    }
    await apiClient.post("/review/link", { week_start: weekStart });
    setUploadMsg(`Uploaded ${done} file(s).`);
    await refresh();
  };

  if (isLoading) return <div className="spinner">Loading the week…</div>;
  if (error) return <div className="error-message">Could not load the week: {error.message}</div>;

  const rows = data.workouts;
  const pending = rows.filter((r) => r.status === "suggested");
  const confirmable = pending.filter((r) => r.match?.name);
  const byDay = rows.reduce((acc, r) => ({ ...acc, [r.date]: [...(acc[r.date] || []), r] }), {});
  const missed = data.planned.filter((p) => !p.done && !rows.some((r) => r.match?.proposed_workout_id === p.id));
  const s = data.sync || {};

  return (
    <div className="week-review">
      <div className="review-toolbar card">
        <div>
          <button className="btn btn-primary" onClick={sync} disabled={s.state === "running"}>
            <RefreshCw size={16} className={s.state === "running" ? "spin" : ""} />
            {s.state === "running" ? "Syncing from TrainingPeaks…" : "Sync from TrainingPeaks"}
          </button>
          <button className="btn btn-outline" onClick={() => fileRef.current?.click()}>
            <Upload size={16} /> Upload files
          </button>
          <input ref={fileRef} type="file" multiple hidden accept=".fit,.FIT,.gz,.csv"
                 onChange={(e) => upload([...e.target.files]).catch((err) => setUploadMsg(`Upload failed: ${err.message}`))} />
        </div>
        <p className="review-status">
          {s.state === "running" && "Takes 1–3 minutes. You can keep reviewing meanwhile."}
          {s.state === "done" && `Last sync ${s.finished?.replace("T", " ")}: ${s.message}`}
          {s.state === "error" && `Sync failed: ${s.message}`}
          {uploadMsg && ` ${uploadMsg}`}
        </p>
      </div>

      <div className="review-summary">
        <span>
          {rows.length - pending.length} of {rows.length} confirmed
        </span>
        {confirmable.length > 0 && (
          <button className="btn btn-secondary btn-sm" onClick={confirmAll}>
            <Check size={14} /> Confirm all suggestions ({confirmable.length})
          </button>
        )}
      </div>

      {rows.length === 0 && <p className="review-empty">No workouts for this week yet — sync or upload first.</p>}

      {Object.entries(byDay).map(([date, dayRows]) => (
        <div key={date} className="review-day">
          <h4>{day(date)}</h4>
          {dayRows.map((r) => (
            <Row key={r.id} row={r} planned={data.planned} categories={data.categories} onMatch={match} />
          ))}
        </div>
      ))}

      {missed.length > 0 && (
        <div className="review-missed">
          <h4>Planned but not matched</h4>
          {missed.map((p) => (
            <p key={p.id}>
              {format(parseISO(p.date), "EEE")} · {p.name}
            </p>
          ))}
        </div>
      )}

      {rows.length > 0 && pending.length === 0 && (
        <button className="btn btn-primary review-continue" onClick={onDone}>
          All confirmed — continue to coaching →
        </button>
      )}
    </div>
  );
}

export default WeekReview;
