import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { addDays, addWeeks, format, parseISO, startOfWeek } from "date-fns";
import { ArrowRight, CheckCircle2, Flag } from "lucide-react";
import { dashboardAPI } from "../api/client";
import { SessionArt, sessionArtKey } from "../components/CoachLogo";
import TodaysCall from "../components/TodaysCall";
import WeatherChip from "../components/WeatherChip";
import WeekStrip from "../components/WeekStrip";
import { useWeather, useWeek } from "../hooks/useWeekData";
import { displayName, mergeDayWorkouts, minutes, tssLabel } from "../lib/workouts";
import { summarizeWeek } from "../lib/weekSummary";
import "../styles/pages.css";
import "./Today.css";

const iso = (d) => format(d, "yyyy-MM-dd");

function greeting(now) {
  const h = now.getHours();
  return h < 5 ? "Up late" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

function SessionCard({ w, monday }) {
  const meta = [w.type, minutes(w) ? `${minutes(w)} min` : null, tssLabel(w)].filter(Boolean).join(" · ");
  return (
    <div className={`card today-session ${w.completed ? "done" : ""}`}>
      {sessionArtKey(w.type, displayName(w)) && <SessionArt type={w.type} name={displayName(w)} size={88} />}
      <div className="today-session-body">
        <span className="today-state">
          {w.completed ? <><CheckCircle2 size={14} /> Done</> : "Planned"}
        </span>
        <h3>{displayName(w)}</h3>
        <p className="today-meta">{meta}</p>
        <Link className="btn btn-primary" to={`/calendar?week=${iso(monday)}&open=${w.key}`}>
          {w.completed ? "See how it went" : "Open workout"} <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}

function Today() {
  const now = new Date();
  const monday = startOfWeek(now, { weekStartsOn: 1 });
  const todayStr = iso(now);
  const { data: week } = useWeek(monday);
  const { data: nextWeek } = useWeek(addWeeks(monday, 1));
  const { data: weather = {} } = useWeather(monday);
  const { data: trends } = useQuery({ queryKey: ["trends"], queryFn: async () => (await dashboardAPI.getTrends(16)).data });

  const sessions = week ? mergeDayWorkouts(week.proposed, week.completed, todayStr) : [];
  const upcoming = [1, 2, 3].map((n) => {
    const d = addDays(now, n);
    const src = iso(startOfWeek(d, { weekStartsOn: 1 })) === iso(monday) ? week : nextWeek;
    const list = src ? mergeDayWorkouts(src.proposed, src.completed, iso(d)).filter((w) => minutes(w) > 0 || w.completed) : [];
    return { date: d, list };
  });
  const summary = week ? summarizeWeek({ proposed: week.proposed, completed: week.completed, plan: week.plan, weather, today: todayStr }) : null;
  const strip = summary && [
    summary.band && { label: "Load", value: `${summary.tss} TSS`, bar: { value: summary.tss, min: summary.band.min, max: summary.band.max }, sub: `plan ${summary.band.min}-${summary.band.max}` },
    summary.planned > 0 && { label: "Planned sessions done", value: `${summary.matched} of ${summary.planned}`, tone: summary.missed ? "warn" : "good" },
  ];
  const next = trends?.goals?.next;
  const hasPlan = week && week.proposed.length > 0;

  return (
    <div className="page-container today-page">
      <div className="page-header">
        <div className="today-header">
          <div>
            <p className="today-date">{format(now, "EEEE, MMMM d")}</p>
            <h1 className="page-title">{greeting(now)}</h1>
          </div>
          <WeatherChip day={weather[todayStr]} />
        </div>
      </div>

      {trends && <TodaysCall load={trends.load} readiness={trends.readiness} />}

      <h2 className="today-h2">Today's training</h2>
      {week && sessions.length === 0 && (
        <div className="card today-empty">
          <p>{hasPlan ? "Nothing planned today: a rest day." : "There is no plan for this week yet."}</p>
          {!hasPlan && <Link className="btn btn-primary" to="/coaching">Plan the week with Coach Claude <ArrowRight size={16} /></Link>}
        </div>
      )}
      {sessions.map((w) => <SessionCard key={w.key} w={w} monday={monday} />)}

      {strip && <WeekStrip items={strip} />}

      {upcoming.some((u) => u.list.length > 0) && (
        <>
          <h2 className="today-h2">Coming up</h2>
          <ul className="today-upcoming">
            {upcoming.filter((u) => u.list.length > 0).map(({ date, list }) => (
              <li key={iso(date)}>
                <Link to={`/calendar?week=${iso(startOfWeek(date, { weekStartsOn: 1 }))}&open=${list[0].key}`}>
                  <span className="up-day">{format(date, "EEE d")}</span>
                  <span className="up-names">{list.map(displayName).join(" · ")}</span>
                </Link>
                <WeatherChip day={weather[iso(date)]} />
              </li>
            ))}
          </ul>
        </>
      )}

      {next && (
        <div className="card today-goal">
          <Flag size={20} />
          <div>
            <strong>{next.description}</strong>
            <span>{next.days_until === 0 ? "today" : `in ${next.days_until} days`}{next.target_date ? " · " : ""}{next.target_date ? format(parseISO(next.target_date), "MMM d") : ""}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default Today;
