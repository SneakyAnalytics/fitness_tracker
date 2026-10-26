import { useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { resolvePowerTarget } from "../lib/workouts";
import "./IntervalVisualizer.css";

// Validated pair (scripts/validate_palette.js): planned vs actual.
const PLANNED = "#e58a4a";   // target band: copper
const ACTUAL = "#3fd0e0";    // what you rode: cyan
const TICK = { fontSize: 12, fill: "rgba(232, 241, 238, 0.7)" };

// Steps on a numeric time axis: a steady/range interval is flat at its band's
// middle; only real ramps slope. `actuals` (optional) adds what was ridden.
export function buildSeries(intervals, ftp, actuals = []) {
  const planned = [];
  const actual = [];
  let t = 0;
  intervals.forEach((iv, i) => {
    const dur = (iv.duration || 0) / 60;
    if (dur <= 0) return;
    const target = resolvePowerTarget(iv.powerTarget, ftp);
    const isRamp = Boolean(iv.powerTarget?.start && iv.powerTarget?.end);
    const name = iv.name || `Interval ${i + 1}`;
    if (target) {
      // Shade the whole target band so riding anywhere inside it reads as on target.
      const start = isRamp ? [target.low, target.low] : [target.low, target.high];
      const end = isRamp ? [target.high, target.high] : [target.low, target.high];
      planned.push({ time: t, planned: start.map(Math.round), name, target: target.label });
      planned.push({ time: t + dur, planned: end.map(Math.round), name, target: target.label });
    }
    const a = actuals.find((r) => r.interval_index === i);
    if (a?.actual_avg_w != null) {
      actual.push({ time: t, actual: Math.round(a.actual_avg_w), name });
      actual.push({ time: t + dur, actual: Math.round(a.actual_avg_w), name });
    }
    t += dur;
  });
  return { planned, actual, total: t };
}

/**
 * One entry per interval, in minutes on the chart's time axis, for hovering a whole interval at once.
 * `actuals` (optional) are the computed rows from interval_results.
 */
export function buildSpans(intervals, ftp, actuals = []) {
  const spans = [];
  let t = 0;
  intervals.forEach((iv, i) => {
    const dur = (iv.duration || 0) / 60;
    if (dur <= 0) return;
    const target = resolvePowerTarget(iv.powerTarget, ftp);
    const a = actuals.find((r) => r.interval_index === i);
    spans.push({
      index: i, start: t, end: t + dur, seconds: iv.duration, name: iv.name || `Interval ${i + 1}`,
      target: target?.label ?? null,
      actual: a?.actual_avg_w != null ? Math.round(a.actual_avg_w) : null,
      deviation: a?.deviation_pct ?? null, compliance: a?.compliance ?? null,
    });
    t += dur;
  });
  return spans;
}

/** The span a time (minutes) falls in; boundaries belong to the interval that is starting. */
export function spanAt(spans, minutes) {
  return spans.find((s) => minutes >= s.start && minutes < s.end) ?? null;
}

const clock = (sec) => `${Math.floor(sec / 60)}:${String(Math.round(sec % 60)).padStart(2, "0")}`;
const WORDS = { on_target: "on target", close: "close to target", low: "below target", high: "above target", missing: "not ridden" };

function SpanTip({ span, total }) {
  // keep the card inside the chart whichever interval is hovered
  const center = Math.min(85, Math.max(15, ((span.start + span.end) / 2 / total) * 100));
  return (
    <div className="iv-tip" style={{ left: `${center}%` }} role="status">
      <h4>{span.name}</h4>
      <p><strong>{clock(span.seconds)}</strong> · {span.target ? <>target <strong>{span.target}</strong></> : "no power target"}</p>
      {span.actual != null && (
        <p>
          rode <strong>{span.actual} W</strong>
          {span.deviation != null && span.deviation !== 0 && <> ({Math.abs(span.deviation)}% {span.deviation > 0 ? "over" : "under"} the band)</>}
          {span.compliance && <span className={`iv-flag ${span.compliance}`}>{WORDS[span.compliance] ?? span.compliance}</span>}
        </p>
      )}
    </div>
  );
}

function IntervalVisualizer({ intervals, ftp, actuals = [] }) {
  if (!intervals || intervals.length === 0) {
    return (
      <div className="interval-visualizer empty">
        <p>No interval data available</p>
      </div>
    );
  }
  const { planned, actual, total } = buildSeries(intervals, ftp, actuals);
  const spans = buildSpans(intervals, ftp, actuals);
  const [hover, setHover] = useState(null);
  const active = spans.find((x) => x.index === hover) ?? null;
  const legendH = actual.length > 0 ? 28 : 0;
  const peak = Math.max(ftp || 0, ...planned.map((d) => d.planned[1]), ...actual.map((d) => d.actual), 100);
  const ticks = Array.from({ length: Math.floor(total / 15) + 1 }, (_, i) => i * 15);

  return (
    <div className="interval-visualizer">
      <div className="iv-stage">
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart margin={{ top: 10, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="rgba(255, 255, 255, 0.14)" strokeDasharray="3 5" vertical={false} />
          <XAxis
            type="number"
            dataKey="time"
            domain={[0, total]}
            ticks={ticks}
            tickFormatter={(v) => `${v}m`}
            tick={TICK}
            allowDuplicatedCategory={false}
          />
          <YAxis domain={[0, Math.ceil(peak / 50) * 50]} tick={TICK} unit="W" width={56} />
          {actual.length > 0 && <Legend verticalAlign="top" height={28} wrapperStyle={{ color: "#e8f1ee" }} />}
          <ReferenceLine y={ftp} stroke="rgba(232, 241, 238, 0.45)" strokeDasharray="5 5"
                         label={{ value: `FTP ${ftp}W`, position: "insideTopRight", fontSize: 11, fill: "rgba(232, 241, 238, 0.8)" }} />
          {active && <ReferenceArea x1={active.start} x2={active.end} fill="#3fd0e0" fillOpacity={0.16}
                                    stroke="#3fd0e0" strokeOpacity={0.7} ifOverflow="visible" />}
          <Area data={planned} dataKey="planned" name="Target band" type="linear" stroke={PLANNED} strokeWidth={1.5}
                fill={PLANNED} fillOpacity={0.3} isAnimationActive={false} />
          {actual.length > 0 && (
            <Line data={actual} dataKey="actual" name="Actual" type="linear" stroke={ACTUAL} strokeWidth={2.5}
                  dot={false} isAnimationActive={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      {/* hover zones: each interval's full width over the plot area (left = y-axis 56px, right margin 16px) */}
      <div className="iv-zones" style={{ top: 10 + legendH, bottom: 4 + 30 }} onMouseLeave={() => setHover(null)}>
        {spans.map((x) => (
          <button
            key={x.index}
            type="button"
            className={`iv-zone ${hover === x.index ? "active" : ""}`}
            style={{ left: `${(x.start / total) * 100}%`, width: `${((x.end - x.start) / total) * 100}%` }}
            aria-label={`${x.name}: ${clock(x.seconds)}${x.target ? `, target ${x.target}` : ""}${x.actual != null ? `, rode ${x.actual} watts` : ""}`}
            onMouseEnter={() => setHover(x.index)}
            onFocus={() => setHover(x.index)}
            onBlur={() => setHover(null)}
            onClick={() => setHover((h) => (h === x.index ? null : x.index))}
          />
        ))}
        {active && <SpanTip span={active} total={total} />}
      </div>
      </div>
    </div>
  );
}

export default IntervalVisualizer;
