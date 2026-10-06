import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3 } from "lucide-react";
import { format, parseISO } from "date-fns";
import { dashboardAPI } from "../api/client";
import "../styles/pages.css";
import "./Dashboard.css";

// Validated (scripts/validate_palette.js): forest/gravel failed chroma + contrast.
const SERIES_RECENT = "#2a78d6";
const SERIES_PRIOR = "#eb6834";
const BAR_FILL = "var(--color-forest)";
const LINE_STROKE = "var(--color-mountain)";
const AXIS = { stroke: "var(--color-text-tertiary)", fontSize: 12 };
const DURATIONS = [
  ["p5s", "5s"],
  ["p1m", "1m"],
  ["p5m", "5m"],
  ["p20m", "20m"],
  ["p60m", "60m"],
];
const TYPES = [
  ["threshold", "Threshold"],
  ["sweet_spot", "Sweet spot"],
  ["over_under", "Over/under"],
  ["vo2max", "VO2max"],
  ["tempo", "Tempo"],
  ["endurance", "Endurance"],
];

const fmtWeek = (d) => format(parseISO(d), "MMM d");
const signed = (n) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n}`);

function Tile({ label, value, sub }) {
  return (
    <div className="stat-tile card">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {sub && <span className="stat-sub">{sub}</span>}
    </div>
  );
}

function PowerCurve({ curve }) {
  const hasPrior = (curve.year_ago?.rides || 0) > 0;
  const rows = DURATIONS.map(([key, label]) => ({
    label,
    recent: curve.recent?.[key] ? Math.round(curve.recent[key]) : null,
    prior: curve.year_ago?.[key] ? Math.round(curve.year_ago[key]) : null,
    change: curve.change_pct?.[key],
  }));
  return (
    <div className="card chart-card">
      <h3>Best power — last {curve.window_days} days{hasPrior ? " vs a year ago" : ""}</h3>
      {!hasPrior && (
        <p className="chart-note">No ride files from a year ago yet (the FIT archive starts in late 2025).</p>
      )}
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows} barGap={2}>
          <CartesianGrid stroke="var(--color-cream-dark)" vertical={false} />
          <XAxis dataKey="label" tick={AXIS} axisLine={false} tickLine={false} />
          <YAxis tick={AXIS} axisLine={false} tickLine={false} unit="W" width={56} />
          <Tooltip cursor={{ fill: "var(--color-cream)" }} formatter={(v) => (v == null ? "—" : `${v} W`)} />
          {hasPrior && <Legend />}
          <Bar dataKey="recent" name={`Last ${curve.window_days} days`} fill={SERIES_RECENT} radius={[4, 4, 0, 0]} maxBarSize={36} />
          {hasPrior && <Bar dataKey="prior" name="Year ago" fill={SERIES_PRIOR} radius={[4, 4, 0, 0]} maxBarSize={36} />}
        </BarChart>
      </ResponsiveContainer>
      <table className="data-table">
        <thead>
          <tr>
            <th>Duration</th>
            <th>Recent</th>
            <th>Year ago</th>
            <th>Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <td>{r.label}</td>
              <td>{r.recent ?? "—"} W</td>
              <td>{r.prior ?? "—"}</td>
              <td>{r.change == null ? "—" : `${signed(r.change)}%`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Progression({ progression }) {
  const types = TYPES.filter(([key]) => (progression[key] || []).length > 0);
  return (
    <div className="card">
      <h3>Key-session progression</h3>
      <p className="chart-note">Work intervals only, oldest → newest. Each one should be a step up from the last.</p>
      <div className="progression-grid">
        {types.map(([key, label]) => (
          <div key={key}>
            <h4>{label}</h4>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Structure</th>
                  <th>Avg W</th>
                  <th>%FTP</th>
                  <th>Work</th>
                  <th>Exec</th>
                </tr>
              </thead>
              <tbody>
                {progression[key].map((s) => (
                  <tr key={s.workout_date}>
                    <td>{fmtWeek(s.workout_date)}</td>
                    <td>{s.structure}</td>
                    <td>{Math.round(s.work_avg_power)}</td>
                    <td>{s.pct_ftp ? `${Math.round(s.pct_ftp * 100)}%` : "—"}</td>
                    <td>{Math.round(s.work_seconds / 60)} min</td>
                    <td>{s.execution_score ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}

function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["trends"],
    queryFn: async () => (await dashboardAPI.getTrends(16)).data,
  });

  if (isLoading) return <div className="page-container spinner">Loading trends…</div>;
  if (error) return <div className="page-container error-message">Could not load trends: {error.message}</div>;

  const { load, weekly, power_curve: curve, zwift_ftp: zftp, readiness, progression } = data;
  const m = readiness?.metrics || {};

  return (
    <div className="page-container dashboard-page">
      <div className="page-header">
        <h1 className="page-title">
          <BarChart3 size={28} /> Training Dashboard
        </h1>
      </div>

      <div className="tile-row">
        <Tile label="Fitness (CTL)" value={Math.round(load.ctl)}
              sub={load.ctl_year_ago != null ? `year ago ${Math.round(load.ctl_year_ago)}` : null} />
        <Tile label="Fatigue (ATL)" value={Math.round(load.atl)} />
        <Tile label="Form (TSB)" value={signed(Math.round(load.tsb))} />
        <Tile label="CTL ramp" value={`${signed(load.ctl_ramp_28d_per_week)}/wk`} sub="last 4 weeks" />
        <Tile label="Zwift FTP" value={zftp?.ftp ? `${zftp.ftp}W` : "—"}
              sub={zftp?.test_due ? `test due · ${zftp.weeks_since_change} wks` : zftp?.changed_on ? `since ${fmtWeek(zftp.changed_on)}` : null} />
        <Tile label="HRV (7d)" value={m.hrv?.last7 ?? "—"}
              sub={m.hrv ? `${signed(m.hrv.change_pct)}% vs baseline` : null} />
        <Tile label="Sleep (7d)" value={m.sleep_hours ? `${m.sleep_hours.last7}h` : "—"} />
      </div>

      {(readiness?.flags?.length > 0 || zftp?.test_due) && (
        <div className="card flags">
          {readiness.flags.map((f) => (
            <p key={f}>⚠️ {f}</p>
          ))}
          {zftp?.test_due && (
            <p>
              ⏱️ Zwift FTP hasn't changed in {zftp.weeks_since_change} weeks — the coach will schedule a Zwift Ramp
              Test (or a race) on a fresh day so Zwift can update it.
            </p>
          )}
        </div>
      )}

      <div className="chart-row">
        <div className="card chart-card">
          <h3>Weekly TSS</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={weekly}>
              <CartesianGrid stroke="var(--color-cream-dark)" vertical={false} />
              <XAxis dataKey="week_start" tickFormatter={fmtWeek} tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} />
              <Tooltip cursor={{ fill: "var(--color-cream)" }} labelFormatter={(d) => `Week of ${fmtWeek(d)}`}
                       formatter={(v) => [`${Math.round(v)} TSS`, "Load"]} />
              <Bar dataKey="tss" fill={BAR_FILL} radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card chart-card">
          <h3>Fitness (CTL) at end of week</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={weekly}>
              <CartesianGrid stroke="var(--color-cream-dark)" vertical={false} />
              <XAxis dataKey="week_start" tickFormatter={fmtWeek} tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} allowDecimals={false}
                     domain={[(min) => Math.floor(min - 5), (max) => Math.ceil(max + 5)]} />
              <Tooltip labelFormatter={(d) => `Week of ${fmtWeek(d)}`} formatter={(v) => [Math.round(v), "CTL"]} />
              <Line type="monotone" dataKey="ctl_end" stroke={LINE_STROKE} strokeWidth={2}
                    dot={{ r: 4, strokeWidth: 2, fill: "var(--color-surface)" }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <PowerCurve curve={curve} />
      <Progression progression={progression} />
    </div>
  );
}

export default Dashboard;
