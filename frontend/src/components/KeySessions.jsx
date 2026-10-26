import React from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format, parseISO } from "date-fns";
import { ArrowDownRight, ArrowRight, ArrowUpRight, Trophy } from "lucide-react";
import { ArtByKey } from "./CoachLogo";
import { summarizeProgression } from "../lib/progression";
import "./KeySessions.css";

// archetype -> label, its badge (CoachLogo), accent colour for its chart
const TYPES = [
  ["threshold", "Threshold", "threshold", "#8af0bd"],
  ["sweet_spot", "Sweet spot", "sweet_spot", "#f4d27a"],
  ["over_under", "Over / unders", "over_under", "#e58a4a"],
  ["vo2max", "VO2max", "vo2max", "#ff8fa3"],
  ["tempo", "Tempo", "tempo", "#8be3ee"],
  ["endurance", "Endurance", "endurance", "#7fb2ff"],
];

const fmtDate = (d) => format(parseISO(d), "MMM d");
const fmtWork = (sec) => (sec >= 5400 ? `${(sec / 3600).toFixed(1)} h` : `${Math.round(sec / 60)} min`);

const TREND = {
  up: { Icon: ArrowUpRight, text: "trending up", cls: "up" },
  flat: { Icon: ArrowRight, text: "holding steady", cls: "flat" },
  down: { Icon: ArrowDownRight, text: "trending down", cls: "down" },
  new: { Icon: ArrowRight, text: "first session logged", cls: "flat" },
};

function SessionTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const s = payload[0].payload;
  return (
    <div className="ks-tip">
      <strong>{fmtDate(s.workout_date)}</strong>
      <span>{s.structure}</span>
      <span>{Math.round(s.work_avg_power)} W{s.pct_ftp ? ` · ${Math.round(s.pct_ftp * 100)}% FTP` : ""}</span>
      <span>Execution {s.execution_score ?? "n/a"}</span>
    </div>
  );
}

function SessionCard({ id, label, art, color, sessions }) {
  const sum = summarizeProgression(sessions);
  const trend = TREND[sum.trend];
  const gradientId = `ks-${id}`;
  const watts = sessions.map((s) => s.work_avg_power);
  const lo = Math.floor((Math.min(...watts) - 15) / 10) * 10;
  const hi = Math.ceil((Math.max(...watts) + 15) / 10) * 10;
  const { latest } = sum;

  return (
    <article className="ks-card card panel-dark">
      <header className="ks-head">
        <ArtByKey name={art} size={64} />
        <div>
          <h4>{label}</h4>
          <span className={`ks-trend ${trend.cls}`}>
            <trend.Icon size={14} /> {trend.text}
            {sum.sinceFirst != null && sum.sinceFirst !== 0 && (
              <> · {sum.sinceFirst > 0 ? "+" : ""}{sum.sinceFirst} W since {fmtDate(sum.first.workout_date)}</>
            )}
          </span>
        </div>
      </header>

      <div className="ks-latest">
        <span className="ks-watts">{Math.round(latest.work_avg_power)}<small> W</small></span>
        {sum.deltaW != null && (
          <span className={`ks-delta ${sum.deltaW > 0 ? "up" : sum.deltaW < 0 ? "down" : "flat"}`}>
            {sum.deltaW > 0 ? "▲" : sum.deltaW < 0 ? "▼" : "•"} {Math.abs(sum.deltaW)} W vs last
          </span>
        )}
      </div>
      <p className="ks-sub">
        {latest.structure} · {fmtWork(latest.work_seconds)} of work
        {latest.pct_ftp ? ` · ${Math.round(latest.pct_ftp * 100)}% FTP` : ""} · {fmtDate(latest.workout_date)}
      </p>

      {sessions.length > 1 && (
        <div className="ks-chart">
          <ResponsiveContainer width="100%" height={92}>
            <AreaChart data={sessions} margin={{ top: 8, right: 10, bottom: 0, left: 10 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.45} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="workout_date" hide />
              <YAxis domain={[lo, hi]} hide />
              <Tooltip content={<SessionTooltip />} cursor={{ stroke: "rgba(255,255,255,0.3)" }} />
              <Area type="monotone" dataKey="work_avg_power" stroke={color} strokeWidth={2.5} fill={`url(#${gradientId})`}
                    dot={{ r: 3.5, strokeWidth: 2, stroke: color, fill: "#0e1d2c" }}
                    activeDot={{ r: 5.5, stroke: "#fff", strokeWidth: 2, fill: color }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <footer className="ks-foot">
        <span className="ks-chip" title="Best average power in this kind of session">
          <Trophy size={13} /> Best {Math.round(sum.best.work_avg_power)} W · {fmtDate(sum.best.workout_date)}
        </span>
        <span className="ks-execs" title="Execution score of each session, oldest to newest">
          {sessions.map((s) => (
            <i key={s.workout_date} className={`ks-exec ${s.execution_score >= 9 ? "great" : s.execution_score >= 6 ? "ok" : "low"}`}
               title={`${fmtDate(s.workout_date)}: execution ${s.execution_score ?? "n/a"}`} />
          ))}
        </span>
      </footer>

      <details className="ks-details">
        <summary>All {sessions.length} sessions</summary>
        <table className="ks-table">
          <thead>
            <tr><th>Date</th><th>Structure</th><th>Avg W</th><th>%FTP</th><th>Exec</th></tr>
          </thead>
          <tbody>
            {[...sessions].reverse().map((s) => (
              <tr key={s.workout_date}>
                <td>{fmtDate(s.workout_date)}</td>
                <td>{s.structure}</td>
                <td>{Math.round(s.work_avg_power)}</td>
                <td>{s.pct_ftp ? `${Math.round(s.pct_ftp * 100)}%` : "n/a"}</td>
                <td>{s.execution_score ?? "n/a"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </article>
  );
}

/** One card per kind of key session: today's number, change vs the last one, a trend line and the history. */
export default function KeySessions({ progression }) {
  const cards = TYPES.filter(([key]) => (progression?.[key] || []).length > 0);
  if (cards.length === 0) return null;
  return (
    <section className="key-sessions">
      <div className="ks-title">
        <h3>Key sessions</h3>
        <p className="chart-note">
          Average power across each session's work intervals (openers and Zone 2 flushes excluded). Each one should be a step
          up from the last, or hold steady while the work grows.
        </p>
      </div>
      <div className="ks-grid">
        {cards.map(([key, label, art, color]) => (
          <SessionCard key={key} id={key} label={label} art={art} color={color} sessions={progression[key]} />
        ))}
      </div>
    </section>
  );
}
