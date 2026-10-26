import React from "react";
import { CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format, parseISO } from "date-fns";
import { withRollingMean } from "../lib/readiness";
import "./ReadinessChart.css";

// metric key -> title, unit, line colour, which direction is good (for the "now" tone)
const PANELS = [
  { key: "hrv", title: "HRV", unit: "ms", color: "#8af0bd", good: "high", note: "Band = 10% either side of your baseline." },
  { key: "resting_hr", title: "Resting heart rate", unit: "bpm", color: "#ff8fa3", good: "low", note: "Band = 5% either side of your baseline." },
  { key: "sleep_hours", title: "Sleep", unit: "h", color: "#7fb2ff", good: "high", note: "Dashed line = the 7 hour target." },
  { key: "body_battery", title: "Body Battery (morning peak)", unit: "", color: "#f4d27a", good: "high", note: "Dashed line = your baseline." },
];
const AXIS = { fill: "rgba(232, 241, 238, 0.7)", fontSize: 11 };
const fmtDay = (d) => format(parseISO(d), "MMM d");

function Panel({ spec, days, base }) {
  const data = withRollingMean(days, spec.key).filter((d) => d[spec.key] != null);
  if (data.length < 2) return null;
  const avgKey = `${spec.key}Avg`;
  const values = data.map((d) => d[spec.key]);
  const refs = [base?.low, base?.high, base?.baseline, base?.target].filter((v) => v != null);
  const lo = Math.floor(Math.min(...values, ...refs) - 2);
  const hi = Math.ceil(Math.max(...values, ...refs) + 2);
  const latest = [...data].reverse().find((d) => d[avgKey] != null) || data[data.length - 1];
  const nowValue = latest[avgKey] ?? latest[spec.key];
  const diff = base?.baseline != null ? Math.round((nowValue - base.baseline) * 10) / 10 : null;
  const better = diff != null && diff !== 0 && (spec.good === "high" ? diff > 0 : diff < 0);

  return (
    <div className="rd-panel">
      <div className="rd-head">
        <h4>{spec.title}</h4>
        <span className="rd-now">
          {nowValue}<small> {spec.unit} · 7-day avg</small>
          {diff != null && <span className={`rd-diff ${diff === 0 ? "" : better ? "good" : "bad"}`}>{diff > 0 ? "+" : ""}{diff} vs baseline</span>}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={130}>
        <ComposedChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.1)" strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="date" tickFormatter={fmtDay} tick={AXIS} axisLine={false} tickLine={false} minTickGap={36} />
          <YAxis domain={[lo, hi]} tick={AXIS} axisLine={false} tickLine={false} width={44} allowDecimals={false} />
          {base?.low != null && <ReferenceArea y1={base.low} y2={base.high} fill="#3fd0e0" fillOpacity={0.13} />}
          {base?.baseline != null && <ReferenceLine y={base.baseline} stroke="rgba(232,241,238,0.45)" strokeDasharray="5 5" />}
          {base?.target != null && <ReferenceLine y={base.target} stroke="#7fb2ff" strokeDasharray="5 5" />}
          <Tooltip
            contentStyle={{ background: "#0e1d2c", border: "1px solid rgba(63,208,224,0.45)", borderRadius: 8, color: "#e8f1ee" }}
            labelStyle={{ color: "#8be3ee", fontWeight: 600 }} itemStyle={{ color: "#e8f1ee" }}
            labelFormatter={fmtDay} formatter={(v, name) => [`${v} ${spec.unit}`.trim(), name]}
          />
          <Line type="monotone" dataKey={spec.key} stroke={spec.color} strokeOpacity={0.35} strokeWidth={1.2} dot={false} connectNulls
                activeDot={{ r: 4, stroke: "#fff", strokeWidth: 1.5, fill: spec.color }} isAnimationActive={false} name="Daily" />
          <Line type="monotone" dataKey={avgKey} stroke={spec.color} strokeWidth={3} dot={false} connectNulls
                activeDot={{ r: 5, stroke: "#fff", strokeWidth: 2, fill: spec.color }} isAnimationActive={false} name="7-day average" />
        </ComposedChart>
      </ResponsiveContainer>
      <p className="rd-note">Faint line = each day, bold = 7-day average. {spec.note}</p>
    </div>
  );
}

/** Daily HRV, resting heart rate, sleep and Body Battery against each baseline, so a trend is visible before a flag fires. */
export default function ReadinessChart({ series }) {
  if (!series?.days?.length) return null;
  const first = series.days[0].date;
  return (
    <section className="card panel-dark readiness-chart">
      <h3>Readiness over time</h3>
      <p className="chart-note">
        The last {series.window_days} days (from {fmtDay(first)}). The highlighted band is the normal range around your own
        baseline: drifting outside it for several days is what raises a flag on the dashboard.
      </p>
      <div className="rd-grid">
        {PANELS.map((p) => (
          <Panel key={p.key} spec={p} days={series.days} base={series.baselines?.[p.key]} />
        ))}
      </div>
    </section>
  );
}
