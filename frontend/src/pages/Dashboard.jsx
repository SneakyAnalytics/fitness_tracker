import React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CoachDashboard } from "../components/CoachLogo";
import Achievements from "../components/Achievements";
import MetricTile from "../components/MetricTile";
import KeySessions from "../components/KeySessions";
import PowerProfile from "../components/PowerProfile";
import ReadinessChart from "../components/ReadinessChart";
import FtpTestCard from "../components/FtpTestCard";
import { Link } from "react-router-dom";
import TodaysCall from "../components/TodaysCall";
import { differenceInCalendarDays, format, parseISO } from "date-fns";
import apiClient, { dashboardAPI } from "../api/client";
import "../styles/pages.css";
import "./Dashboard.css";

// Charts sit on dark instrument panels: bright gradient fills with a soft glow (see theme.css).
const CYAN = "#3fd0e0";
const COPPER = "#e58a4a";
const AXIS = { fill: "rgba(232, 241, 238, 0.7)", fontSize: 12 };
const GRID = { stroke: "rgba(255, 255, 255, 0.14)", strokeDasharray: "3 5", vertical: false };
const CURSOR = { fill: "rgba(63, 208, 224, 0.09)" };
const TOOLTIP = {
  contentStyle: {
    background: "#0e1d2c",
    border: "1px solid rgba(63, 208, 224, 0.45)",
    borderRadius: 8,
    color: "#e8f1ee",
    boxShadow: "0 6px 18px rgba(0, 0, 0, 0.35)",
  },
  labelStyle: { color: "#8be3ee", fontWeight: 600 },
  itemStyle: { color: "#e8f1ee" },
};

function Gradient({ id, top, bottom, topOpacity = 1, bottomOpacity = 1 }) {
  return (
    <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={top} stopOpacity={topOpacity} />
      <stop offset="100%" stopColor={bottom} stopOpacity={bottomOpacity} />
    </linearGradient>
  );
}

const fmtWeek = (d) => format(parseISO(d), "MMM d");
const signed = (n) => (n == null ? "—" : `${n > 0 ? "+" : ""}${n}`);

function Consistency({ consistency }) {
  const weeks = consistency?.weeks || [];
  if (weeks.length === 0) return null;
  const hits = weeks.filter((w) => w.status === "hit").length;
  const planned = weeks.filter((w) => w.status !== "none").length;
  return (
    <div className="card panel-dark consistency">
      <h3>Consistency</h3>
      <div className="consistency-body">
        <div className="streak">
          <span className="streak-number">{consistency.streak}</span>
          <span className="streak-label">week streak</span>
        </div>
        <div>
          <ol className="pips" aria-label="Plan adherence by week">
            {weeks.map((w) => (
              <li key={w.week_start} className={`pip ${w.status}`}
                  title={`Week of ${fmtWeek(w.week_start)}: ${Math.round(w.tss)} TSS` +
                         (w.planned_min ? ` (plan ${w.planned_min}-${w.planned_max})` : " (no plan)")} />
            ))}
          </ol>
          <p className="chart-note">
            {hits} of {planned} planned weeks landed within 15% of the plan's TSS band.
          </p>
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["trends"],
    queryFn: async () => (await dashboardAPI.getTrends(16)).data,
  });

  if (isLoading) return <div className="page-container spinner">Loading trends…</div>;
  if (error) return <div className="page-container error-message">Could not load trends: {error.message}</div>;

  // After a Zwift ramp test, tell the app what Zwift now shows; it stands until later rides clearly disagree.
  const confirmFtp = async () => {
    const entered = window.prompt("What does Zwift show as your FTP now? (watts)", String(data.zwift_ftp?.ftp ?? ""));
    if (entered == null) return;
    const ftp = parseInt(entered, 10);
    if (!Number.isFinite(ftp)) {
      window.alert("Enter a number of watts, for example 321.");
      return;
    }
    const test = data.zwift_ftp?.last_test_or_race;
    const recentTest = test && differenceInCalendarDays(new Date(), parseISO(test)) <= 14;
    try {
      await apiClient.post("/zwift_ftp/confirm", { ftp, date: recentTest ? test : undefined });
      await queryClient.invalidateQueries();
    } catch (err) {
      window.alert(err.response?.data?.detail || err.message);
    }
  };

  const { load, weekly, power_profile, zwift_ftp: zftp, readiness, readiness_series, progression, goals, consistency } = data;
  const m = readiness?.metrics || {};

  return (
    <div className="page-container dashboard-page">
      <div className="page-header">
        <div className="hero-title">
          <CoachDashboard size={116} />
          <h1 className="page-title">Training Dashboard</h1>
        </div>
        <Link to="/metrics" className="guide-link">What do these numbers mean?</Link>
      </div>

      <div className="tile-row">
        <MetricTile metricId="ctl" label="Fitness (CTL)" value={Math.round(load.ctl)} raw={load.ctl}
                    sub={load.ctl_year_ago != null ? `year ago ${Math.round(load.ctl_year_ago)}` : null} />
        <MetricTile metricId="atl" label="Fatigue (ATL)" value={Math.round(load.atl)} raw={load.atl} />
        <MetricTile metricId="tsb" label="Form (TSB)" value={signed(Math.round(load.tsb))} raw={load.tsb} />
        <MetricTile metricId="ramp" label="CTL ramp" value={`${signed(load.ctl_ramp_28d_per_week)}/wk`}
                    raw={load.ctl_ramp_28d_per_week} sub="last 4 weeks" />
        <MetricTile metricId="ftp" label="Zwift FTP" value={zftp?.ftp ? `${zftp.ftp}W` : "—"} raw={zftp?.ftp ?? null}
                    action={{ label: "Confirm FTP from Zwift", onClick: confirmFtp }}
                    sub={zftp?.test_due ? `test due · ${zftp.weeks_since_change} wks` : zftp?.changed_on ? `${zftp.source === "confirmed" ? "confirmed " : ""}since ${fmtWeek(zftp.changed_on)}` : null} />
        <MetricTile metricId="hrv" label="HRV (7d)" value={m.hrv?.last7 ?? "—"} raw={m.hrv?.last7 ?? null}
                    ctx={{ changePct: m.hrv?.change_pct }} sub={m.hrv ? `${signed(m.hrv.change_pct)}% vs baseline` : null} />
        <MetricTile metricId="sleep" label="Sleep (7d)" value={m.sleep_hours ? `${m.sleep_hours.last7}h` : "—"}
                    raw={m.sleep_hours?.last7 ?? null} />
      </div>

      <TodaysCall load={load} readiness={readiness} />

      <FtpTestCard zftp={zftp} />

      <div className="chart-row">
        <div className="card chart-card panel-dark">
          <h3>Weekly TSS</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={weekly}>
              <defs>
                <Gradient id="tssFill" top="#8af0bd" bottom="#2a8a5e" />
              </defs>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="week_start" tickFormatter={fmtWeek} tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} />
              <Tooltip {...TOOLTIP} cursor={CURSOR} labelFormatter={(d) => `Week of ${fmtWeek(d)}`}
                       formatter={(v) => [`${Math.round(v)} TSS`, "Load"]} />
              <Bar dataKey="tss" fill="url(#tssFill)" radius={[6, 6, 0, 0]} maxBarSize={28} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card chart-card panel-dark">
          <h3>Fitness (CTL) at end of week</h3>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={weekly}>
              <defs>
                <Gradient id="ctlFill" top={CYAN} bottom={CYAN} topOpacity={0.45} bottomOpacity={0} />
              </defs>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="week_start" tickFormatter={fmtWeek} tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} allowDecimals={false}
                     domain={[(min) => Math.floor(min - 5), (max) => Math.ceil(max + 5)]} />
              <Tooltip {...TOOLTIP} labelFormatter={(d) => `Week of ${fmtWeek(d)}`} formatter={(v) => [Math.round(v), "CTL"]} />
              <Area type="monotone" dataKey="ctl_end" stroke={CYAN} strokeWidth={3} fill="url(#ctlFill)"
                    dot={{ r: 4, strokeWidth: 2, stroke: CYAN, fill: "#0e1d2c" }}
                    activeDot={{ r: 6, stroke: "#fff", strokeWidth: 2, fill: CYAN }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <ReadinessChart series={readiness_series} />

      <Consistency consistency={consistency} />

      <Achievements goals={goals} />

      <PowerProfile profile={power_profile} />
      <KeySessions progression={progression} />
    </div>
  );
}

export default Dashboard;
