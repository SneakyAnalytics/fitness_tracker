import { useState } from "react";
import { CheckCircle2, ChevronDown, ChevronRight, ExternalLink, Save } from "lucide-react";
import { exerciseLookupUrl } from "../lib/workouts";
import "./ExerciseDetail.css";

function formatDuration(seconds) {
  if (!seconds) return null;
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  }
  return `${seconds}s`;
}

const range = (v) => (typeof v === "object" && v ? `${v.min ?? v.value}-${v.max ?? v.value}` : v);

// Numbers get a unit; descriptions like "moderate" or "bodyweight" stay as written.
export function formatWeight(w) {
  if (w == null || w === "") return null;
  if (typeof w === "object") return `${range(w)} ${w.unit || "lbs"}`;
  return /^\d+(\.\d+)?$/.test(String(w).trim()) ? `${w} lbs` : String(w);
}

const isNumberish = (v) => /^\d+(\s*-\s*\d+)?$/.test(String(v).trim());
// "12" -> "12 reps"; "10 each leg" or "30-40 seconds" are already descriptive.
const reps = (v, side) => (isNumberish(range(v)) ? `${range(v)} reps${side}` : `${range(v)}${side && !/each/.test(String(v)) ? side : ""}`);

function describeSet(s) {
  const side = s.perSide ? " each side" : "";
  return [
    s.reps && reps(s.reps, side),
    s.targetReps && reps(s.targetReps, side),
    s.duration && `${formatDuration(s.duration)}${side}`,
    s.workTime && `${s.workTime}s on`,
    s.restTime && `${s.restTime}s off`,
    formatWeight(s.weight),
    s.restBetweenSets && `rest ${s.restBetweenSets}s`,
  ]
    .filter(Boolean)
    .join(" · ");
}

// One line such as "3 × 10 each leg · moderate". Identical sets are grouped.
export function prescription(exercise) {
  const sets = Array.isArray(exercise.sets) ? exercise.sets : [];
  const groups = [];
  sets.forEach((s) => {
    const text = describeSet(s);
    const count = Number(s.sets) || 1;
    const last = groups[groups.length - 1];
    if (last && last.text === text) last.count += count;
    else groups.push({ text, count });
  });
  return groups
    .filter((g) => g.text)
    .map((g) => (g.count > 1 ? `${g.count} × ${g.text}` : g.text))
    .join("  |  ");
}

function NoteList({ title, items, className }) {
  if (!Array.isArray(items) || items.length === 0) return null;
  return (
    <div className={className}>
      <strong>{title}</strong>
      <ul>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function ExerciseDetail({ exercise, initialLog = {}, onSave }) {
  const [open, setOpen] = useState(false);
  const [reps, setReps] = useState(initialLog.reps || "");
  const [weight, setWeight] = useState(initialLog.weight || "");
  const [notes, setNotes] = useState(initialLog.notes || "");
  const [logged, setLogged] = useState(Boolean(initialLog.reps || initialLog.weight || initialLog.notes));
  const [status, setStatus] = useState("");
  const sets = Array.isArray(exercise.sets) ? exercise.sets : [];
  const summary = prescription(exercise);

  const handleSave = async () => {
    if (!onSave) return;
    setStatus("Saving…");
    try {
      await onSave(exercise.id, { reps, weight, notes });
      setStatus("Saved ✓");
      setLogged(true);
    } catch (err) {
      setStatus(`Save failed: ${err.message}`);
    }
  };

  return (
    <div className={`exercise-detail ${open ? "open" : ""} ${logged ? "logged" : ""}`}>
      <div className="exercise-header">
        <button className="exercise-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          <span className="exercise-info">
            <span className="exercise-name">
              {exercise.name}
              {logged && <CheckCircle2 size={16} className="exercise-logged-icon" />}
            </span>
            {summary && <span className="exercise-summary">{summary}</span>}
          </span>
        </button>
        <a
          href={exerciseLookupUrl(exercise.name)}
          target="_blank"
          rel="noopener noreferrer"
          className="exercise-link"
          title="Look up how to do this exercise"
          aria-label={`Look up ${exercise.name}`}
        >
          <ExternalLink size={18} />
        </a>
      </div>

      {open && (
        <div className="exercise-body">
          {exercise.description && <p className="exercise-description">{exercise.description}</p>}
          {sets.map((set, idx) => (
            <div key={idx} className="exercise-set-notes">
              {sets.length > 1 && <strong className="set-label">Set {idx + 1}</strong>}
              <NoteList title="Notes" items={set.notes} className="set-notes" />
              <NoteList title="Cues" items={set.cues} className="set-cues" />
            </div>
          ))}
          <NoteList title="Form cues" items={exercise.cues} className="exercise-cues" />

          <div className="exercise-inputs">
            <div className="input-group">
              <label htmlFor={`reps-${exercise.id}`}>Reps done</label>
              <input id={`reps-${exercise.id}`} type="text" className="input" value={reps}
                     onChange={(e) => setReps(e.target.value)} placeholder="e.g. 10,10,8" />
            </div>
            <div className="input-group">
              <label htmlFor={`weight-${exercise.id}`}>Weight (lbs)</label>
              <input id={`weight-${exercise.id}`} type="text" className="input" value={weight}
                     onChange={(e) => setWeight(e.target.value)} placeholder="e.g. 135" />
            </div>
          </div>
          <div className="input-group">
            <label htmlFor={`notes-${exercise.id}`}>Notes</label>
            <textarea id={`notes-${exercise.id}`} className="input textarea" value={notes} rows={2}
                      onChange={(e) => setNotes(e.target.value)} placeholder="How did it feel?" />
          </div>
          <button className="btn btn-primary btn-sm" onClick={handleSave}>
            <Save size={16} />
            Save
          </button>
          {status && <span className="save-status">{status}</span>}
        </div>
      )}
    </div>
  );
}

export default ExerciseDetail;
