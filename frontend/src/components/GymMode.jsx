import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowLeft, ArrowRight, Check, ExternalLink, Plus, SkipForward, X } from "lucide-react";
import { beep, ding, audio } from "../lib/sounds";
import { clock, expandSets, restSeconds, sessionProgress } from "../lib/gym";
import { exerciseLookupUrl, movementTiming } from "../lib/workouts";
import { describeSet, prescription } from "./ExerciseDetail";
import MovementTimer from "./MovementTimer";
import "./GymMode.css";

/**
 * Full-screen, one-exercise-at-a-time view for the gym: big "set done" button, a rest countdown after
 * every set, and the weight/reps you used saved with the same call the exercise list uses.
 */
export default function GymMode(props) {
  // Portal to <body>: the page-transition wrapper has a transform, which would trap a fixed overlay inside the page.
  return createPortal(<GymSession {...props} />, document.body);
}

function GymSession({ title, exercises, logs = {}, onSave, onClose }) {
  const [idx, setIdx] = useState(0);
  const [done, setDone] = useState({});               // exercise index -> sets completed
  const [rest, setRest] = useState(null);             // { endsAt, total } while resting
  const [now, setNow] = useState(Date.now());
  const [entries, setEntries] = useState(() => ({ ...logs })); // exercise id -> { weight, reps, notes }
  const [finished, setFinished] = useState(false);
  const [saveError, setSaveError] = useState("");
  const lastBeep = useRef(null);

  const exercise = exercises[idx];
  const sets = expandSets(exercise);
  const completed = done[idx] || 0;
  const timing = movementTiming(exercise);
  const entry = entries[exercise.id] || {};
  const leftSec = rest ? Math.max(0, Math.ceil((rest.endsAt - now) / 1000)) : 0;

  useEffect(() => {
    // keep the screen awake for the whole session
    let lock = null;
    navigator.wakeLock?.request?.("screen").then((l) => { lock = l; }).catch(() => {});
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      lock?.release?.().catch(() => {});
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  useEffect(() => {
    if (!rest) return undefined;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [rest]);

  useEffect(() => {
    if (!rest) return;
    if (leftSec > 0 && leftSec <= 3 && lastBeep.current !== leftSec) {
      lastBeep.current = leftSec;
      beep(880, 90);
    }
    if (leftSec === 0) {
      lastBeep.current = null;
      ding();
      navigator.vibrate?.([200, 100, 200]);
      setRest(null);
    }
  }, [rest, leftSec]);

  const startRest = (seconds) => {
    audio();
    setNow(Date.now());
    setRest({ endsAt: Date.now() + seconds * 1000, total: seconds });
  };

  const setDoneTap = () => {
    const n = completed + 1;
    setDone((d) => ({ ...d, [idx]: n }));
    if (n < sets.length) startRest(restSeconds(exercise));
    else setRest(null);
  };

  const update = (field, value) => setEntries((e) => ({ ...e, [exercise.id]: { ...(e[exercise.id] || {}), [field]: value } }));

  // Weight/reps are saved when you leave an exercise, and only if you typed something (never blank an old log).
  const persist = async () => {
    const e = entries[exercise.id];
    if (!onSave || !e || !(e.weight || e.reps || e.notes)) return true;
    try {
      await onSave(exercise.id, { reps: e.reps || "", weight: e.weight || "", notes: e.notes || "" });
      setSaveError("");
      return true;
    } catch (err) {
      setSaveError(`Could not save ${exercise.name}: ${err.message}`);
      return false;
    }
  };

  const go = async (next) => {
    if (!(await persist())) return;
    setRest(null);
    if (next >= exercises.length) setFinished(true);
    else setIdx(Math.max(0, next));
  };

  const progress = sessionProgress(exercises, done);

  if (finished) {
    return (
      <div className="gym" role="dialog" aria-modal="true" aria-label="Workout complete">
        <div className="gym-finish">
          <Check size={64} />
          <h2>Workout complete</h2>
          <p>{exercises.length} exercises · {Math.round(progress * 100)}% of sets ticked off. Weights and reps you entered are saved.</p>
          <button className="gym-big" onClick={onClose}>Done</button>
        </div>
      </div>
    );
  }

  const summary = prescription(exercise);
  const last = idx === exercises.length - 1;
  const allSetsDone = completed >= sets.length;

  return (
    <div className="gym" role="dialog" aria-modal="true" aria-label={`Gym mode: ${title}`}>
      <header className="gym-top">
        <button className="gym-icon" onClick={onClose} aria-label="Close gym mode"><X size={26} /></button>
        <div className="gym-heading">
          <strong>{title}</strong>
          <span>Exercise {idx + 1} of {exercises.length}</span>
        </div>
      </header>
      <div className="gym-progress" role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100}>
        <span style={{ width: `${progress * 100}%` }} />
      </div>

      <main className="gym-body">
        {exercise.section && <span className="gym-section">{exercise.section}</span>}
        <h2 className="gym-name">{exercise.name}</h2>
        {summary && <p className="gym-rx">{summary}</p>}

        <ol className="gym-sets" aria-label="Sets">
          {sets.map((s, i) => (
            <li key={i} className={i < completed ? "done" : i === completed ? "current" : ""}>
              <span className="gym-set-n">{i < completed ? <Check size={16} /> : i + 1}</span>
              <span className="gym-set-text">{describeSet(s) || "Set"}</span>
            </li>
          ))}
        </ol>

        {timing && <MovementTimer seconds={timing.seconds} perSide={timing.perSide} />}

        {rest ? (
          <div className="gym-rest" aria-live="polite">
            <span className="gym-rest-label">Rest</span>
            <span className="gym-rest-time">{clock(leftSec)}</span>
            <div className="gym-rest-bar"><span style={{ width: `${(leftSec / rest.total) * 100}%` }} /></div>
            <div className="gym-rest-actions">
              <button onClick={() => setRest((r) => ({ ...r, endsAt: r.endsAt + 15000, total: r.total + 15 }))}><Plus size={16} /> 15 s</button>
              <button onClick={() => setRest(null)}><SkipForward size={16} /> Skip rest</button>
            </div>
          </div>
        ) : !allSetsDone ? (
          <button className="gym-big" onClick={setDoneTap}>Set {completed + 1} done</button>
        ) : (
          <button className="gym-big" onClick={() => go(idx + 1)}>{last ? "Finish workout" : "Next exercise"} <ArrowRight size={22} /></button>
        )}

        <div className="gym-log">
          <label>Weight used<input className="input" inputMode="decimal" value={entry.weight || ""} onChange={(e) => update("weight", e.target.value)} placeholder="lbs" /></label>
          <label>Reps done<input className="input" value={entry.reps || ""} onChange={(e) => update("reps", e.target.value)} placeholder="e.g. 10, 10, 8" /></label>
        </div>
        {saveError && <p className="gym-error">{saveError}</p>}

        {Array.isArray(exercise.cues) && exercise.cues.length > 0 && (
          <ul className="gym-cues">{exercise.cues.map((c, i) => <li key={i}>{c}</li>)}</ul>
        )}
        <a className="gym-link" href={exerciseLookupUrl(exercise.name)} target="_blank" rel="noopener noreferrer">
          How to do this <ExternalLink size={14} />
        </a>
      </main>

      <footer className="gym-nav">
        <button className="gym-nav-btn" disabled={idx === 0} onClick={() => go(idx - 1)}><ArrowLeft size={18} /> Back</button>
        {!allSetsDone && !last && <button className="gym-nav-btn" onClick={() => go(idx + 1)}>Skip <ArrowRight size={18} /></button>}
      </footer>
    </div>
  );
}
