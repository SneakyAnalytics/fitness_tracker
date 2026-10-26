import React from "react";
import "./WeekStrip.css";

/**
 * A slim "this week" strip under a page title. Each item is { label, value, sub?, tone?, bar? } where
 * bar is { value, min, max } to draw progress against a target band.
 */
export default function WeekStrip({ items, label = "This week" }) {
  const shown = items.filter(Boolean);
  if (!shown.length) return null;
  return (
    <section className="week-strip" aria-label={label}>
      <span className="week-strip-label">{label}</span>
      {shown.map((it) => (
        <div key={it.label} className={`ws-item ${it.tone || ""}`}>
          <span className="ws-value">{it.value}</span>
          <span className="ws-name">{it.label}</span>
          {it.bar && <Bar {...it.bar} />}
          {it.sub && <span className="ws-sub">{it.sub}</span>}
        </div>
      ))}
    </section>
  );
}

function Bar({ value, min, max }) {
  const top = Math.max(max * 1.15, value * 1.05, 1);
  const pct = (n) => `${Math.min(100, (n / top) * 100)}%`;
  const state = value > max ? "over" : value >= min ? "in" : "under";
  return (
    <span className="ws-bar" role="img" aria-label={`${value} of ${min} to ${max}`}>
      <i className="ws-band" style={{ left: pct(min), width: `calc(${pct(max)} - ${pct(min)})` }} />
      <i className={`ws-fill ${state}`} style={{ width: pct(value) }} />
    </span>
  );
}
