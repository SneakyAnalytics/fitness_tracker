/*
 * Coach Claude's sounds, synthesised with Web Audio (no audio files): a referee's whistle for
 * "plan saved" and the coach starting to answer, and a bell-like ding for timers.
 * A mute switch (top bar) is remembered in localStorage.
 */
const KEY = "coach-claude-muted";
let ctx = null;

export function isMuted() {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function setMuted(muted) {
  try {
    localStorage.setItem(KEY, muted ? "1" : "0");
  } catch {
    /* private mode: the choice just won't persist */
  }
}

// Browsers (iOS especially) only allow sound after a tap, so the context is created on first use.
export function audio() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  if (!ctx) ctx = new Ctx();
  if (ctx.state === "suspended") ctx.resume();
  return ctx;
}

function envelope(gain, t, peak, attack, hold, release) {
  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(peak, t + attack);
  gain.gain.setValueAtTime(peak, t + attack + hold);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + attack + hold + release);
}

/** A plain tone, used for the last-three-seconds ticks. */
export function beep(freq, ms, delay = 0) {
  if (isMuted()) return;
  const c = audio();
  if (!c) return;
  const osc = c.createOscillator();
  const gain = c.createGain();
  osc.frequency.value = freq;
  osc.connect(gain);
  gain.connect(c.destination);
  const t = c.currentTime + delay / 1000;
  envelope(gain, t, 0.35, 0.01, 0, ms / 1000);
  osc.start(t);
  osc.stop(t + ms / 1000 + 0.05);
}

/** Referee whistle: a ~2.9 kHz tone with a fast trill (the pea) and a little breath noise. */
export function whistle({ seconds = 0.55, volume = 0.3 } = {}) {
  if (isMuted()) return;
  const c = audio();
  if (!c) return;
  const t = c.currentTime;
  const master = c.createGain();
  master.connect(c.destination);
  envelope(master, t, volume, 0.04, seconds * 0.55, seconds * 0.4);

  const carrier = c.createOscillator();
  carrier.type = "sine";
  carrier.frequency.setValueAtTime(2850, t);
  carrier.frequency.linearRampToValueAtTime(3050, t + seconds * 0.3);
  const trill = c.createOscillator();         // 34 Hz wobble of the pitch
  trill.frequency.value = 34;
  const depth = c.createGain();
  depth.gain.value = 140;
  trill.connect(depth);
  depth.connect(carrier.frequency);
  carrier.connect(master);

  const noise = c.createBufferSource();       // breath: short band-passed noise
  const buf = c.createBuffer(1, Math.ceil(c.sampleRate * seconds), c.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < data.length; i += 1) data[i] = Math.random() * 2 - 1;
  noise.buffer = buf;
  const band = c.createBiquadFilter();
  band.type = "bandpass";
  band.frequency.value = 3200;
  band.Q.value = 2;
  const breath = c.createGain();
  breath.gain.value = 0.18;
  noise.connect(band);
  band.connect(breath);
  breath.connect(master);

  [carrier, trill, noise].forEach((n) => {
    n.start(t);
    n.stop(t + seconds + 0.05);
  });
}

/** A short pip, for the coach starting to answer. */
export function peep() {
  whistle({ seconds: 0.16, volume: 0.16 });
}

/** Timer finished: two bell notes with inharmonic partials so it rings rather than beeps. */
export function ding(delay = 0) {
  if (isMuted()) return;
  const c = audio();
  if (!c) return;
  [[1046.5, 0], [1318.5, 0.26]].forEach(([freq, offset]) => {
    const t = c.currentTime + delay / 1000 + offset;
    [[1, 0.34], [2.76, 0.12], [5.4, 0.05]].forEach(([mult, peak]) => {
      const osc = c.createOscillator();
      const gain = c.createGain();
      osc.frequency.value = freq * mult;
      osc.connect(gain);
      gain.connect(c.destination);
      envelope(gain, t, peak, 0.005, 0, 0.9 / mult ** 0.35);
      osc.start(t);
      osc.stop(t + 1.2);
    });
  });
}
