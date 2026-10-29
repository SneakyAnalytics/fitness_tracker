import { useEffect, useRef, useState } from "react";
import { Pause, Play, Plus, SkipForward } from "lucide-react";
import { beep, ding, audio } from "../lib/sounds";
import { clock } from "../lib/gym";
import "./HoldTimer.css";

const SWITCH_SECONDS = 5;

/**
 * One big timer for a stretch or hold: runs each side and set in turn, beeps the last three seconds, dings at the end of
 * each hold and gives a short "switch" gap before starting the next one by itself. `onStep(n)` reports holds finished.
 */
export default function HoldTimer({ steps, onStep }) {
  const [step, setStep] = useState(0);            // hold in progress; steps.length once everything is done
  const [phase, setPhase] = useState("idle");     // idle | run | pause | switch | done
  const [endsAt, setEndsAt] = useState(0);
  const [frozen, setFrozen] = useState(0);        // seconds left when paused
  const [now, setNow] = useState(Date.now());
  const lastBeep = useRef(null);
  const current = steps[Math.min(step, steps.length - 1)];
  const left = phase === "pause" ? frozen : Math.max(0, Math.ceil((endsAt - now) / 1000));

  useEffect(() => {
    if (phase !== "run" && phase !== "switch") return undefined;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [phase]);

  const begin = (seconds, nextPhase) => { setNow(Date.now()); setEndsAt(Date.now() + seconds * 1000); setPhase(nextPhase); };

  useEffect(() => {
    if (phase !== "run" && phase !== "switch") return;
    if (left > 0 && left <= 3 && lastBeep.current !== `${phase}${left}`) { lastBeep.current = `${phase}${left}`; beep(880, 90); }
    if (left > 0) return;
    lastBeep.current = null;
    ding();
    navigator.vibrate?.([200, 100, 200]);
    if (phase === "switch") { begin(current.seconds, "run"); return; }
    const finished = step + 1;
    onStep(finished);
    setStep(finished);
    if (finished >= steps.length) setPhase("done"); else begin(SWITCH_SECONDS, "switch");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, left]);

  const start = () => { audio(); begin(current.seconds, "run"); };
  const pause = () => { setFrozen(left); setPhase("pause"); };
  const resume = () => begin(frozen, "run");
  const more = () => { setEndsAt((t) => t + 15000); if (phase === "pause") setFrozen((f) => f + 15); };
  const skip = () => { setEndsAt(Date.now()); setNow(Date.now() + 1); };      // finish this hold (or the switch gap) now

  if (phase === "done") return <div className="hold hold-done">All holds done</div>;

  const next = steps[step + 1];
  const label = phase === "switch" ? `Next: ${current.side ? `${current.side} side` : "next set"}` : current.side ? `${current.side} side` : "Hold";
  const setText = steps.some((s) => s.set > 0) ? ` · set ${current.set + 1}` : "";

  return (
    <div className={`hold ${phase}`} aria-live="polite">
      <span className="hold-label">{label}{phase === "switch" ? "" : setText}</span>
      <span className="hold-time">{phase === "idle" ? clock(current.seconds) : clock(left)}</span>
      <span className="hold-count">{step + 1} of {steps.length}{next && phase !== "switch" ? ` · then ${next.side ? `${next.side} side` : "next set"}` : ""}</span>
      <div className="hold-actions">
        {phase === "idle" && <button className="hold-go" onClick={start}><Play size={22} /> Start</button>}
        {phase === "run" && <button className="hold-go" onClick={pause}><Pause size={22} /> Pause</button>}
        {phase === "pause" && <button className="hold-go" onClick={resume}><Play size={22} /> Resume</button>}
        {phase === "switch" && <button className="hold-go" onClick={skip}><Play size={22} /> Start now</button>}
        {(phase === "run" || phase === "pause") && <button onClick={more}><Plus size={16} /> 15 s</button>}
        {(phase === "run" || phase === "pause") && <button onClick={skip}><SkipForward size={16} /> Done</button>}
      </div>
    </div>
  );
}
