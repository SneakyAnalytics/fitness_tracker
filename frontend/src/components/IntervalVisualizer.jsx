import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { resolvePowerTarget } from "../lib/workouts";
import "./IntervalVisualizer.css";

// Validated pair (scripts/validate_palette.js): planned vs actual.
const PLANNED = "#eb6834";
const ACTUAL = "#2a78d6";

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

function TooltipBody({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="interval-tooltip">
      <h4>{p.name}</h4>
      {payload.map((s) => (
        <p key={s.dataKey}>
          <strong>{s.dataKey === "planned" ? "Target" : "Actual"}:</strong>{" "}
          {s.dataKey === "planned" && p.target ? p.target : `${s.value}W`}
        </p>
      ))}
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
  const peak = Math.max(ftp || 0, ...planned.map((d) => d.planned[1]), ...actual.map((d) => d.actual), 100);
  const ticks = Array.from({ length: Math.floor(total / 15) + 1 }, (_, i) => i * 15);

  return (
    <div className="interval-visualizer">
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart margin={{ top: 10, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--color-cream-dark)" vertical={false} />
          <XAxis
            type="number"
            dataKey="time"
            domain={[0, total]}
            ticks={ticks}
            tickFormatter={(v) => `${v}m`}
            tick={{ fontSize: 12 }}
            allowDuplicatedCategory={false}
          />
          <YAxis domain={[0, Math.ceil(peak / 50) * 50]} tick={{ fontSize: 12 }} unit="W" width={56} />
          <Tooltip content={<TooltipBody />} />
          {actual.length > 0 && <Legend verticalAlign="top" height={28} />}
          <ReferenceLine y={ftp} stroke="var(--color-text-tertiary)" strokeDasharray="5 5"
                         label={{ value: `FTP ${ftp}W`, position: "insideTopRight", fontSize: 11 }} />
          <Area data={planned} dataKey="planned" name="Target band" type="linear" stroke={PLANNED} strokeWidth={1.5}
                fill={PLANNED} fillOpacity={0.25} isAnimationActive={false} />
          {actual.length > 0 && (
            <Line data={actual} dataKey="actual" name="Actual" type="linear" stroke={ACTUAL} strokeWidth={2}
                  dot={false} isAnimationActive={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export default IntervalVisualizer;
