import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, ArrowRight, Check, Plus, SkipForward, X } from "lucide-react";
import { gymAPI } from "../api/client";
import { beep, ding, audio } from "../lib/sounds";
import { clock, cuesFor, describeSession, expandSets, logEntry, restSeconds, saveErrorMessage, sessionProgress, suggestWeight, targetRepsTop } from "../lib/gym";
import { movementTiming } from "../lib/workouts";
import { describeSet, prescription } from "./ExerciseDetail";
import ExerciseCarousel from "./ExerciseCarousel";
import MovementTimer from "./MovementTimer";
import "./GymMode.css";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Full-screen, one-exercise-at-a-time view for the gym: per-set weight and reps (prefilled from last time),
 * the plan's cues, photos of the movement, a rest countdown after every set, and a save that retries quietly
 * instead of getting in the way.
 */
export default function GymMode(props) {
  // Portal to <body>: the page-transition wrapper has a transform, which would trap a fixed overlay inside the page.
  return createPortal(<GymSession {...props} />, document.body);
}

function GymSession({ title, date, exercises, logs = {}, onSave, onClose }) {
  const [idx, setIdx] = useState(0);
  const [done, setDone] = useState({});                // exercise index -> sets ticked
  const [rest, setRest] = useState(null);              // { endsAt, total } while resting
  const [now, setNow] = useState(Date.now());
  const [finished, setFinished] = useState(false);
  const [typed, setTyped] = useState(() => {           // exercise id -> [{weight, reps}] values (typed or confirmed)
    const out = {};
    Object.entries(logs).forEach(([id, l]) => { if (Array.isArray(l?.sets)) out[id] = l.sets.map((s) => ({ weight: String(s.weight ?? ""), reps: String(s.reps ?? "") })); });
    return out;
  });
  const [pending, setPending] = useState({});          // exercise id -> { ex, entry, message } still to be saved
  const lastBeep = useRef(null);
  const chain = useRef(Promise.resolve());

  const names = exercises.map((e) => e.name);
  const { data: lastData } = useQuery({
    queryKey: ["strength-last", date, names.join("|")],
    queryFn: async () => (await gymAPI.last(names, date)).data.last,
    staleTime: 60 * 1000,
  });
  const last = lastData || {};

  const exercise = exercises[idx];
  const sets = expandSets(exercise);
  const completed = done[idx] || 0;
  const timing = movementTiming(exercise);
  const lastSession = last[exercise.name];
  const suggestion = suggestWeight(lastSession, targetRepsTop(sets[0]));
  const leftSec = rest ? Math.max(0, Math.ceil((rest.endsAt - now) / 1000)) : 0;

  // Value shown in a set's box: what was typed, else the previous set's weight (or the suggestion), else the rep target.
  const valueOf = (ex, exIdx, i, field) => {
    const v = typed[ex.id]?.[i]?.[field];
    if (v !== undefined) return v;
    if (field === "weight") {
      if (i > 0) return valueOf(ex, exIdx, i - 1, "weight");
      const s = suggestWeight(last[ex.name], targetRepsTop(expandSets(ex)[0]));
      return s ? String(s.weight) : "";
    }
    const top = targetRepsTop(expandSets(ex)[i]);
    return top != null ? String(top) : "";
  };
  const edit = (i, field, value) => setTyped((t) => {
    const rows = [...(t[exercise.id] || [])];
    for (let k = 0; k <= i; k += 1) rows[k] = rows[k] || { weight: valueOf(exercise, idx, k, "weight"), reps: valueOf(exercise, idx, k, "reps") };
    rows[i] = { ...rows[i], [field]: value };
    return { ...t, [exercise.id]: rows };
  });

  const ticked = (ex, exIdx, count) => Array.from({ length: count }, (_, i) => ({ weight: valueOf(ex, exIdx, i, "weight"), reps: valueOf(ex, exIdx, i, "reps") }));

  // ── saving: sequential (the API stores one record per workout), retried, never blocks navigation ──
  const saveExercise = useCallback((ex, entry) => {
    if (!onSave || !entry) return Promise.resolve();
    const run = async () => {
      let failure;
      for (let attempt = 0; attempt < 3; attempt += 1) {
        try {
          await onSave(ex.id, entry);
          setPending((p) => { const { [ex.id]: _gone, ...rest2 } = p; return rest2; });
          return;
        } catch (err) {
          failure = err;
          await sleep(attempt === 0 ? 800 : 2000);
        }
      }
      setPending((p) => ({ ...p, [ex.id]: { ex, entry, message: saveErrorMessage(failure) } }));
    };
    chain.current = chain.current.then(run);
    return chain.current;
  }, [onSave]);

  const saveCurrent = () => saveExercise(exercise, logEntry(exercise, ticked(exercise, idx, completed)));

  const retryAll = useCallback(() => Object.values(pending).forEach((p) => saveExercise(p.ex, p.entry)), [pending, saveExercise]);
  useEffect(() => {
    if (!Object.keys(pending).length) return undefined;
    const id = setInterval(retryAll, 15000);
    window.addEventListener("online", retryAll);
    return () => { clearInterval(id); window.removeEventListener("online", retryAll); };
  }, [pending, retryAll]);

  const close = async () => {
    await saveCurrent();
    await chain.current;
    if (Object.keys(pending).length && !window.confirm("Some entries are not saved yet. Close anyway?")) return;
    onClose();
  };

  useEffect(() => {
    let lock = null;
    navigator.wakeLock?.request?.("screen").then((l) => { lock = l; }).catch(() => {});
    document.body.style.overflow = "hidden";
    return () => { lock?.release?.().catch(() => {}); document.body.style.overflow = ""; };
  }, []);

  useEffect(() => {
    if (!rest) return undefined;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [rest]);

  useEffect(() => {
    if (!rest) return;
    if (leftSec > 0 && leftSec <= 3 && lastBeep.current !== leftSec) { lastBeep.current = leftSec; beep(880, 90); }
    if (leftSec === 0) { lastBeep.current = null; ding(); navigator.vibrate?.([200, 100, 200]); setRest(null); }
  }, [rest, leftSec]);

  const startRest = (seconds) => { audio(); setNow(Date.now()); setRest({ endsAt: Date.now() + seconds * 1000, total: seconds }); };

  const setDoneTap = () => {
    // make what is on screen the record, so later changes to the defaults can't alter a set that was ticked
    setTyped((t) => {
      const rows = [...(t[exercise.id] || [])];
      rows[completed] = { weight: valueOf(exercise, idx, completed, "weight"), reps: valueOf(exercise, idx, completed, "reps") };
      for (let k = 0; k < completed; k += 1) rows[k] = rows[k] || { weight: valueOf(exercise, idx, k, "weight"), reps: valueOf(exercise, idx, k, "reps") };
      return { ...t, [exercise.id]: rows };
    });
    const n = completed + 1;
    setDone((d) => ({ ...d, [idx]: n }));
    if (n < sets.length) startRest(restSeconds(exercise)); else setRest(null);
  };

  const go = (next) => {
    saveCurrent();                                   // not awaited: the next exercise appears immediately
    setRest(null);
    if (next >= exercises.length) setFinished(true); else setIdx(Math.max(0, next));
  };

  const progress = sessionProgress(exercises, done);
  const pendingList = Object.values(pending);
  const failedBanner = pendingList.length > 0 && (
    <div className="gym-warn" role="alert">
      <AlertTriangle size={18} />
      <div>
        <strong>{pendingList.length} {pendingList.length === 1 ? "exercise" : "exercises"} not saved yet</strong>
        <span>{pendingList[0].message}</span>
      </div>
      <button onClick={retryAll}>Retry now</button>
    </div>
  );

  if (finished) {
    return (
      <div className="gym" role="dialog" aria-modal="true" aria-label="Workout complete">
        <div className="gym-finish">
          <Check size={64} />
          <h2>Workout complete</h2>
          <p>{exercises.length} exercises · {Math.round(progress * 100)}% of sets ticked off.</p>
          {pendingList.length === 0 ? <p>Your weights and reps are saved, and the coach will use them to set next week's loads.</p> : failedBanner}
          <button className="gym-big" onClick={async () => { await chain.current; if (!Object.keys(pending).length || window.confirm("Some entries are not saved yet. Close anyway?")) onClose(); }}>Done</button>
        </div>
      </div>
    );
  }

  const summary = prescription(exercise);
  const last_ = idx === exercises.length - 1;
  const allSetsDone = completed >= sets.length;
  const cues = cuesFor(exercise, completed);

  return (
    <div className="gym" role="dialog" aria-modal="true" aria-label={`Gym mode: ${title}`}>
      <header className="gym-top">
        <button className="gym-icon" onClick={close} aria-label="Close gym mode"><X size={26} /></button>
        <div className="gym-heading">
          <strong>{title}</strong>
          <span>Exercise {idx + 1} of {exercises.length}</span>
        </div>
      </header>
      <div className="gym-progress" role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100}>
        <span style={{ width: `${progress * 100}%` }} />
      </div>

      <main className="gym-body">
        {failedBanner}
        {exercise.section && <span className="gym-section">{exercise.section}</span>}
        <h2 className="gym-name">{exercise.name}</h2>
        {summary && <p className="gym-rx">{summary}</p>}

        <div className="gym-last">
          {lastSession ? (
            <>
              <span>Last time ({lastSession.date.slice(5)}): <strong>{describeSession(lastSession)}</strong></span>
              {suggestion && <span className={`gym-suggest ${suggestion.change}`}>Try {suggestion.weight} lb: {suggestion.reason}.</span>}
            </>
          ) : <span>No lifts logged for this movement yet. What you enter here is what the coach will build on.</span>}
        </div>

        <ol className="gym-sets" aria-label="Sets">
          {sets.map((s, i) => (
            <li key={i} className={i < completed ? "done" : i === completed ? "current" : ""}>
              <span className="gym-set-n">{i < completed ? <Check size={16} /> : i + 1}</span>
              <span className="gym-set-text">{describeSet(s) || "Set"}</span>
              <input className="gym-num" inputMode="decimal" aria-label={`Set ${i + 1} weight in pounds`} placeholder="lb"
                     value={valueOf(exercise, idx, i, "weight")} onChange={(e) => edit(i, "weight", e.target.value)} />
              <span className="gym-x">×</span>
              <input className="gym-num" inputMode="numeric" aria-label={`Set ${i + 1} reps`} placeholder="reps"
                     value={valueOf(exercise, idx, i, "reps")} onChange={(e) => edit(i, "reps", e.target.value)} />
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
          <button className="gym-big" onClick={() => go(idx + 1)}>{last_ ? "Finish workout" : "Next exercise"} <ArrowRight size={22} /></button>
        )}

        {(cues.length > 0 || exercise.description) && (
          <section className="gym-cues" aria-label="Cues">
            <h3>{cues.length > 0 ? `Cues${sets.length > 1 ? ` for set ${Math.min(completed + 1, sets.length)}` : ""}` : "About"}</h3>
            {exercise.description && <p>{exercise.description}</p>}
            {cues.length > 0 && <ul>{cues.map((c, i) => <li key={i}>{c}</li>)}</ul>}
          </section>
        )}

        <ExerciseCarousel name={exercise.name} />
      </main>

      <footer className="gym-nav">
        <button className="gym-nav-btn" disabled={idx === 0} onClick={() => go(idx - 1)}><ArrowLeft size={18} /> Back</button>
        {!allSetsDone && !last_ && <button className="gym-nav-btn" onClick={() => go(idx + 1)}>Skip <ArrowRight size={18} /></button>}
      </footer>
    </div>
  );
}
