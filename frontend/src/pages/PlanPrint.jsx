import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { addDays, format, parseISO, startOfWeek } from "date-fns";
import { ArrowLeft, Check, Copy, Printer } from "lucide-react";
import { proposedWorkoutAPI } from "../api/client";
import { CoachBadge } from "../components/CoachLogo";
import { useAthleteSettings } from "../hooks/useAthleteSettings";
import { useWeekParam } from "../hooks/useWeekParam";
import { groupByDay, planAsText, planNotes, sessionDetail, sessionLine } from "../lib/planText";
import "./PlanPrint.css";

/** A clean, light page of one week's plan: print it, save it as a PDF, or copy it as text for a message. */
export default function PlanPrint() {
  const [weekStart] = useWeekParam(startOfWeek(new Date(), { weekStartsOn: 1 }));
  const { ftp } = useAthleteSettings();
  const [copied, setCopied] = useState(false);
  const startStr = format(weekStart, "yyyy-MM-dd");
  const { data, isLoading, error } = useQuery({
    queryKey: ["planPrint", startStr],
    queryFn: async () => (await proposedWorkoutAPI.getWeek(startStr, format(addDays(weekStart, 6), "yyyy-MM-dd"))).data,
  });

  if (isLoading) return <div className="print-page"><p>Loading the plan…</p></div>;
  if (error) return <div className="print-page"><p>Could not load this week: {error.message}</p></div>;

  const plan = data?.weekly_plan || null;
  const workouts = data?.daily_workouts || [];
  const notes = planNotes(plan);
  const days = groupByDay(workouts, weekStart);
  const planFtp = plan?.ftp || ftp;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(planAsText({ weekStart, plan, workouts, ftp: planFtp }));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.alert("Couldn't copy. Use Print and choose Save as PDF instead.");
    }
  };

  return (
    <div className="print-page">
      <div className="print-actions no-print">
        <Link to={`/calendar?week=${startStr}`} className="btn btn-outline"><ArrowLeft size={16} /> Calendar</Link>
        <span className="print-spacer" />
        <button className="btn btn-outline" onClick={copy}>{copied ? <><Check size={16} /> Copied</> : <><Copy size={16} /> Copy as text</>}</button>
        <button className="btn btn-primary" onClick={() => window.print()}><Printer size={16} /> Print / save as PDF</button>
      </div>

      <header className="print-head">
        <CoachBadge size={64} />
        <div>
          <h1>Training plan</h1>
          <p>
            Week of {format(weekStart, "MMM d")} to {format(addDays(weekStart, 6), "MMM d, yyyy")}
            {plan?.plannedTSS_min ? ` · ${plan.plannedTSS_min}-${plan.plannedTSS_max} TSS` : ""}
            {planFtp ? ` · FTP ${planFtp} W` : ""}
          </p>
        </div>
      </header>

      {notes.focus && <p className="print-focus"><strong>Focus.</strong> {notes.focus}</p>}
      {notes.considerations && <p className="print-focus"><strong>This week.</strong> {notes.considerations}</p>}

      <div className="print-days">
        {days.map((day) => (
          <section key={day.date} className="print-day">
            <h2>{day.label}</h2>
            {day.sessions.length === 0 && <p className="print-rest">Rest</p>}
            {day.sessions.map((w) => (
              <div key={w.id} className="print-session">
                <strong>{sessionLine(w)}</strong>
                {sessionDetail(w, planFtp) && <span>{sessionDetail(w, planFtp)}</span>}
              </div>
            ))}
          </section>
        ))}
      </div>
      <footer className="print-foot">Coach Claude · prescribed power assumes an FTP of {planFtp} W</footer>
    </div>
  );
}
