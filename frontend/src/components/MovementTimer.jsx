import { useEffect, useRef, useState } from "react";
import { Pause, Play, RotateCcw } from "lucide-react";
import "./MovementTimer.css";

let audioCtx = null;
// Browsers (iOS especially) only allow sound after a tap, so this is created on Play.
function audio() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  if (!audioCtx) audioCtx = new Ctx();
  if (audioCtx.state === "suspended") audioCtx.resume();
  return audioCtx;
}

function beep(freq, ms, delay = 0) {
  const ctx = audio();
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.frequency.value = freq;
  osc.connect(gain);
  gain.connect(ctx.destination);
  const t = ctx.currentTime + delay / 1000;
  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(0.4, t + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + ms / 1000);
  osc.start(t);
  osc.stop(t + ms / 1000 + 0.02);
}

const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

// Compact countdown for a timed movement: tap ▶, it dings at zero, tap again for the next side/set.
function MovementTimer({ seconds, perSide }) {
  const [preset, setPreset] = useState(seconds);
  const [left, setLeft] = useState(seconds);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(0);
  const endAt = useRef(null);
  const wakeLock = useRef(null);

  useEffect(() => {
    if (!running) return undefined;
    const id = setInterval(() => {
      const remaining = Math.max(0, Math.ceil((endAt.current - Date.now()) / 1000));
      setLeft((prev) => {
        if (remaining !== prev && remaining > 0 && remaining <= 3) beep(880, 90);
        return remaining;
      });
      if (remaining === 0) {
        setRunning(false);
        setDone((d) => d + 1);
        beep(1046, 250);
        beep(1318, 400, 260);
        navigator.vibrate?.([200, 100, 200]);
      }
    }, 200);
    return () => clearInterval(id);
  }, [running]);

  // Keep the phone screen on while counting.
  useEffect(() => {
    if (running && navigator.wakeLock?.request) {
      navigator.wakeLock.request("screen").then((l) => (wakeLock.current = l)).catch(() => {});
    }
    return () => {
      wakeLock.current?.release?.().catch(() => {});
      wakeLock.current = null;
    };
  }, [running]);

  const start = () => {
    audio();
    const from = left > 0 && left < preset && !running ? left : preset; // resume a pause, else restart
    endAt.current = Date.now() + from * 1000;
    setLeft(from);
    setRunning(true);
  };
  const pause = () => setRunning(false);
  const reset = () => {
    setRunning(false);
    setLeft(preset);
  };
  const adjust = (delta) => {
    const next = Math.min(1800, Math.max(5, preset + delta));
    setPreset(next);
    if (!running) setLeft(next);
  };

  return (
    <div className={`movement-timer ${running ? "running" : ""} ${left === 0 ? "finished" : ""}`}>
      {running ? (
        <button className="mt-btn" onClick={pause} aria-label="Pause timer">
          <Pause size={18} />
        </button>
      ) : (
        <button className="mt-btn primary" onClick={start} aria-label="Start timer">
          <Play size={18} />
        </button>
      )}
      <span className="mt-time" aria-live="polite">
        {fmt(left)}
      </span>
      <span className="mt-label">
        {perSide ? "per side" : "hold"}
        {done > 0 && ` · ${done} done`}
      </span>
      {!running && (
        <span className="mt-adjust">
          <button className="mt-small" onClick={() => adjust(-5)} aria-label="5 seconds less">
            −5
          </button>
          <button className="mt-small" onClick={() => adjust(5)} aria-label="5 seconds more">
            +5
          </button>
          {left !== preset && (
            <button className="mt-small" onClick={reset} aria-label="Reset timer">
              <RotateCcw size={14} />
            </button>
          )}
        </span>
      )}
    </div>
  );
}

export default MovementTimer;
