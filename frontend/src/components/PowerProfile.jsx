import React from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format, parseISO } from "date-fns";
import { ArrowDownRight, ArrowUpRight, Minus, Trophy } from "lucide-react";
import "./PowerProfile.css";

const FEEL = { p5s: "Sprint", p1m: "Anaerobic", p5m: "VO2max", p20m: "Threshold", p60m: "Endurance" };
const COLORS = { p5s: "#ff8fa3", p1m: "#e58a4a", p5m: "#f4d27a", p20m: "#8af0bd", p60m: "#7fb2ff" };

const fmtDate = (d) => format(parseISO(d), "MMM d, yyyy");
const fmtMonth = (m) => format(parseISO(`${m}-01`), "MMM yyyy");

function Change({ pct, label }) {
  if (pct == null) return null;
  const dir = pct > 0.5 ? "up" : pct < -0.5 ? "down" : "flat";
  const Icon = dir === "up" ? ArrowUpRight : dir === "down" ? ArrowDownRight : Minus;
  return (
    <span className={`pp-change ${dir}`}>
      <Icon size={14} /> {pct > 0 ? "+" : ""}{pct}% {label}
    </span>
  );
}

function MonthTip({ active, payload }) {
  if (!active || !payload?.length || payload[0].value == null) return null;
  const p = payload[0].payload;
  return (
    <div className="pp-tip">
      <strong>{fmtMonth(p.month)}</strong>
      <span>{p.watts} W best</span>
    </div>
  );
}

function DurationCard({ d, windowDays }) {
  const color = COLORS[d.key];
  const watts = d.monthly.filter((m) => m.watts != null).map((m) => m.watts);
  const lo = watts.length ? Math.floor((Math.min(...watts) - 10) / 10) * 10 : 0;
  const hi = watts.length ? Math.ceil((Math.max(...watts) + 10) / 10) * 10 : 100;
  const isBest = d.recent != null && d.best != null && d.recent >= d.best;

  return (
    <article className="pp-card card panel-dark">
      <header>
        <span className="pp-dur">{d.label}</span>
        <span className="pp-feel">{FEEL[d.key]}</span>
      </header>
      <div className="pp-now">
        {d.recent != null ? <>{d.recent}<small> W</small></> : <span className="pp-none">no rides</span>}
      </div>
      <div className="pp-changes">
        <Change pct={d.change_pct} label={`vs prior ${windowDays} d`} />
        <Change pct={d.year_ago_change_pct} label="vs a year ago" />
        {d.change_pct == null && d.recent != null && <span className="pp-hint">no earlier window to compare</span>}
      </div>
      {watts.length > 1 && (
        <div className="pp-chart">
          <ResponsiveContainer width="100%" height={70}>
            <AreaChart data={d.monthly} margin={{ top: 6, right: 6, bottom: 0, left: 6 }}>
              <defs>
                <linearGradient id={`pp-${d.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.45} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" hide />
              <YAxis domain={[lo, hi]} hide />
              <Tooltip content={<MonthTip />} cursor={{ stroke: "rgba(255,255,255,0.3)" }} />
              <Area type="monotone" dataKey="watts" stroke={color} strokeWidth={2.5} fill={`url(#pp-${d.key})`} connectNulls
                    dot={{ r: 3, strokeWidth: 2, stroke: color, fill: "#0e1d2c" }} activeDot={{ r: 5, stroke: "#fff", strokeWidth: 2, fill: color }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
      <footer>
        {d.best != null && (
          <span className={`pp-best ${isBest ? "now" : ""}`} title="Best average power for this duration in the ride archive">
            <Trophy size={13} /> {isBest ? "Best ever, just now" : `Best ${d.best} W · ${fmtDate(d.best_date)}`}
          </span>
        )}
        {d.year_ago != null && <span className="pp-year">a year ago {d.year_ago} W</span>}
      </footer>
    </article>
  );
}

/** Best power at each duration: the last N days against the N before, best ever, and a 12-month trend. */
export default function PowerProfile({ profile }) {
  if (!profile?.durations?.length) return null;
  const { window_days: days, rides, archive_start: start } = profile;
  return (
    <section className="power-profile">
      <h3>Best power</h3>
      <p className="chart-note">
        Your best average power for each duration over the last {days} days ({rides.recent} rides), against the {days} days before
        ({rides.prior} rides). The line is the best in each of the last 12 months.
        {rides.year_ago === 0 && start ? ` There are no ride files from a year ago yet (the archive starts ${fmtDate(start)}), so that comparison will appear on its own.` : ""}
      </p>
      <div className="pp-grid">
        {profile.durations.map((d) => (
          <DurationCard key={d.key} d={d} windowDays={days} />
        ))}
      </div>
    </section>
  );
}
