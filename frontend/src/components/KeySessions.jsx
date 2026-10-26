import React from "react";
import { useState } from "react";
import { Area, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format, parseISO } from "date-fns";
import { ArrowDownRight, ArrowRight, ArrowUpRight, Trophy } from "lucide-react";
import { ArtByKey } from "./CoachLogo";
import { MODES, summarizeProgression } from "../lib/progression";
import "./KeySessions.css";

// archetype -> label, its badge (CoachLogo), accent colour for its chart
const TYPES = [   // easiest to hardest, following the training zones
  ["endurance", "Endurance", "endurance", "#7fb2ff"],
  ["tempo", "Tempo", "tempo", "#8be3ee"],
  ["sweet_spot", "Sweet spot", "sweet_spot", "#f4d27a"],
  ["threshold", "Threshold", "threshold", "#8af0bd"],
  ["over_under", "Over / unders", "over_under", "#e58a4a"],
  ["vo2max", "VO2max", "vo2max", "#ff8fa3"],
];

const fmtDate = (d) => format(parseISO(d), "MMM d");
const fmtWork = (sec) => (sec >= 5400 ? `${(sec / 3600).toFixed(1)} h` : `${Math.round(sec / 60)} min`);

const TREND = {
  up: { Icon: ArrowUpRight, text: "trending up", cls: "up" },
  flat: { Icon: ArrowRight, text: "holding steady", cls: "flat" },
  down: { Icon: ArrowDownRight, text: "trending down", cls: "down" },
  new: { Icon: ArrowRight, text: "first session logged", cls: "flat" },
};

const pts = (n) => (Math.abs(n) === 1 ? "pt" : "pts");
const num = (n, mode) => (mode === "ftp" ? `${n}%` : `${Math.round(n)} W`);

function SessionTooltip({ active, payload, mode }) {
  if (!active || !payload?.length) return null;
  const s = payload[0].payload;
  return (
    <div className="ks-tip">
      <strong>{fmtDate(s.workout_date)}</strong>
      <span>{s.structure}</span>
      <span>Rode {num(s.value, mode)}{mode === "watts" && s.pct_ftp ? ` · ${Math.round(s.pct_ftp * 100)}% FTP` : ""}</span>
      {s.plan != null && <span>Plan {num(s.plan, mode)}</span>}
      <span>Execution {s.execution_score ?? "n/a"}</span>
    </div>
  );
}

function SessionCard({ id, label, art, color, sessions, mode }) {
  const sum = summarizeProgression(sessions, mode);
  if (!sum) {
    return (
      <article className="ks-card card panel-dark">
        <header className="ks-head"><ArtByKey name={art} size={64} /><div><h4>{label}</h4><span className="ks-trend flat">no FTP on record for these sessions</span></div></header>
      </article>
    );
  }
  const trend = TREND[sum.trend];
  const unit = MODES[mode].unit;
  const gradientId = `ks-${id}`;
  const all = sum.rows.flatMap((r) => [r.value, r.plan]).filter((v) => v != null);
  const pad = mode === "ftp" ? 3 : 15;
  const lo = Math.floor((Math.min(...all) - pad) / 5) * 5;
  const hi = Math.ceil((Math.max(...all) + pad) / 5) * 5;
  const { latest } = sum;
  const hasPlan = sum.rows.some((r) => r.plan != null);

  return (
    <article className="ks-card card panel-dark">
      <header className="ks-head">
        <ArtByKey name={art} size={64} />
        <div>
          <h4>{label}</h4>
          <span className={`ks-trend ${trend.cls}`}>
            <trend.Icon size={14} /> {trend.text}
            {sum.sinceFirst != null && sum.sinceFirst !== 0 && (
              <> · {sum.sinceFirst > 0 ? "+" : ""}{sum.sinceFirst} {mode === "ftp" ? pts(sum.sinceFirst) : "W"} since {fmtDate(sum.first.workout_date)}</>
            )}
          </span>
        </div>
      </header>

      <div className="ks-latest">
        <span className="ks-watts">{mode === "ftp" ? latest.value : Math.round(latest.value)}<small> {unit === "%" ? "% FTP" : unit}</small></span>
        {sum.delta != null && (
          <span className={`ks-delta ${sum.delta > 0 ? "up" : sum.delta < 0 ? "down" : "flat"}`}>
            {sum.delta > 0 ? "▲" : sum.delta < 0 ? "▼" : "•"} {Math.abs(sum.delta)} {mode === "ftp" ? pts(sum.delta) : "W"} vs last
          </span>
        )}
        {sum.vsPlan != null && (
          <span className={`ks-plan-chip ${Math.abs(sum.vsPlan) <= (mode === "ftp" ? 1.5 : 5) ? "ok" : ""}`}
                title="Latest session against the average of the power the plan asked for in its work intervals">
            {sum.vsPlan === 0 ? "on plan" : `${sum.vsPlan > 0 ? "+" : ""}${sum.vsPlan} ${mode === "ftp" ? pts(sum.vsPlan) : "W"} vs plan`}
          </span>
        )}
      </div>
      <p className="ks-sub">
        {latest.structure} · {fmtWork(latest.work_seconds)} of work
        {mode === "watts" && latest.pct_ftp ? ` · ${Math.round(latest.pct_ftp * 100)}% FTP` : ""} · {fmtDate(latest.workout_date)}
      </p>

      {sum.rows.length > 1 && (
        <div className="ks-chart">
          <ResponsiveContainer width="100%" height={92}>
            <ComposedChart data={sum.rows} margin={{ top: 8, right: 10, bottom: 0, left: 10 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.45} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="workout_date" hide />
              <YAxis domain={[lo, hi]} hide />
              <Tooltip content={<SessionTooltip mode={mode} />} cursor={{ stroke: "rgba(255,255,255,0.3)" }} />
              {hasPlan && <Line type="monotone" dataKey="plan" stroke="rgba(255,255,255,0.75)" strokeWidth={1.5} strokeDasharray="4 4"
                                dot={false} connectNulls isAnimationActive={false} />}
              <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} fill={`url(#${gradientId})`}
                    dot={{ r: 3.5, strokeWidth: 2, stroke: color, fill: "#0e1d2c" }}
                    activeDot={{ r: 5.5, stroke: "#fff", strokeWidth: 2, fill: color }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
      {hasPlan && sum.rows.length > 1 && <p className="ks-legend"><i className="ks-key actual" style={{ background: color }} /> rode <i className="ks-key plan" /> plan</p>}

      <footer className="ks-foot">
        <span className="ks-chip" title="Best session of this kind in the list">
          <Trophy size={13} /> Best {mode === "ftp" ? `${sum.best.value}% FTP` : `${Math.round(sum.best.value)} W`} · {fmtDate(sum.best.workout_date)}
        </span>
        <span className="ks-execs" title="Execution score of each session, oldest to newest">
          {sum.rows.map((s) => (
            <i key={s.workout_date} className={`ks-exec ${s.execution_score >= 9 ? "great" : s.execution_score >= 6 ? "ok" : "low"}`}
               title={`${fmtDate(s.workout_date)}: execution ${s.execution_score ?? "n/a"}`} />
          ))}
        </span>
      </footer>

      <details className="ks-details">
        <summary>All {sum.rows.length} sessions</summary>
        <table className="ks-table">
          <thead>
            <tr><th>Date</th><th>Structure</th><th>Rode</th><th>Plan</th><th>Exec</th></tr>
          </thead>
          <tbody>
            {[...sum.rows].reverse().map((s) => (
              <tr key={s.workout_date}>
                <td>{fmtDate(s.workout_date)}</td>
                <td>{s.structure}</td>
                <td>{mode === "ftp" ? `${s.value}%` : Math.round(s.value)}</td>
                <td>{s.plan != null ? (mode === "ftp" ? `${s.plan}%` : Math.round(s.plan)) : "n/a"}</td>
                <td>{s.execution_score ?? "n/a"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </article>
  );
}

const STORE = "coach-claude-keysession-mode";
const savedMode = () => {
  try { return localStorage.getItem(STORE) === "ftp" ? "ftp" : "watts"; } catch { return "watts"; }
};

/** One card per kind of key session: today's number, change vs the last one, a trend line and the history. */
export default function KeySessions({ progression }) {
  const [mode, setModeState] = useState(savedMode);
  const setMode = (m) => {
    setModeState(m);
    try { localStorage.setItem(STORE, m); } catch { /* not persisted */ }
  };
  const cards = TYPES.filter(([key]) => (progression?.[key] || []).length > 0);
  if (cards.length === 0) return null;
  return (
    <section className="key-sessions">
      <div className="ks-title">
        <div className="ks-title-row">
          <h3>Key sessions</h3>
          <div className="ks-toggle" role="group" aria-label="Show power as">
            {Object.entries(MODES).map(([key, m]) => (
              <button key={key} type="button" className={mode === key ? "on" : ""} aria-pressed={mode === key} onClick={() => setMode(key)}>
                {m.label}
              </button>
            ))}
          </div>
        </div>
        <p className="chart-note">
          Average power across each session's work intervals (openers and Zone 2 flushes excluded), easiest type to hardest. The dashed line is what the plan asked for. Each session should be a step up from the last, or hold steady while the work grows. % of FTP compares each session with the FTP it was prescribed against, so a change in FTP doesn't look like progress.
        </p>
      </div>
      <div className="ks-grid">
        {cards.map(([key, label, art, color]) => (
          <SessionCard key={key} id={key} label={label} art={art} color={color} sessions={progression[key]} mode={mode} />
        ))}
      </div>
    </section>
  );
}
