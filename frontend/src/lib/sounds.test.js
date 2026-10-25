import { beforeEach, describe, expect, it, vi } from "vitest";
import { ding, isMuted, setMuted, whistle } from "./sounds";

function fakeAudio() {
  const made = { osc: 0, noise: 0 };
  const param = () => ({ value: 0, setValueAtTime: vi.fn(), linearRampToValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() });
  const node = () => ({ connect: vi.fn(), start: vi.fn(), stop: vi.fn(), gain: param(), frequency: param(), Q: param() });
  window.AudioContext = function Ctx() {
    this.state = "running";
    this.currentTime = 0;
    this.sampleRate = 8000;
    this.destination = {};
    this.createOscillator = () => { made.osc += 1; return node(); };
    this.createGain = node;
    this.createBiquadFilter = node;
    this.createBufferSource = () => { made.noise += 1; return node(); };
    this.createBuffer = (_c, n) => ({ getChannelData: () => new Float32Array(n) });
  };
  return made;
}

describe("sounds", () => {
  beforeEach(() => localStorage.clear());

  it("remembers the mute switch", () => {
    expect(isMuted()).toBe(false);
    setMuted(true);
    expect(isMuted()).toBe(true);
  });

  it("plays a whistle and a ding when unmuted", () => {
    const made = fakeAudio();
    whistle();
    expect(made.osc).toBe(2);       // carrier + trill
    expect(made.noise).toBe(1);
    ding();
    expect(made.osc).toBe(2 + 6);   // two notes x three partials
  });

  it("is silent when muted", () => {
    const made = fakeAudio();
    setMuted(true);
    whistle();
    ding();
    expect(made.osc + made.noise).toBe(0);
  });
});
