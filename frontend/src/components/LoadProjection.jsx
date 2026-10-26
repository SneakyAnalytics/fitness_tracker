import React from "react";
import { Area, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format, parseISO } from "date-fns";
import { formLabel, formOn, lowestForm, plannedDayCount, projectionData } from "../lib/loadProjection";
import "./LoadProjection.css";

const CYAN = "#3fd0e0";
const COPPER = "#e58a4a";
const GREEN = "#8af0bd";
const AXIS = { fill: "rgba(232, 241, 238, 0.7)", fontSize: 11 };
const fmtDay = (d) => format(parseISO(d), "MMM d");
const TOOLTIP = {
  contentStyle: { background: "#0e1d2c", border: "1px solid rgba(63,208,224,0.45)", borderRadius: 8, color: "#e8f1ee" },
  labelStyle: { color: "#8be3ee", fontWeight: 600 },
  itemStyle: { color: "#e8f1ee" },
};
const NAMES = { ctl: "Fitness (CTL)", atl: "Fatigue (ATL)", tsb: "Form (TSB)" };

// Past and projected values are separate series; show whichever exists for the hovered day, once.
const tooltipFormatter = (value, name) => {
  const base = name.replace(" (projected)", "");
  return [Math.round(value), name.includes("projected") ? `${base} · projected` : base];
};

/**
 * Fitness, fatigue and form for the last 90 days, then the next 4 weeks projected from the saved plan
 * (dashed). Days with no plan yet assume the recent average, and the chart says where that starts.
 * Two charts, not one with two axes: CTL/ATL share a unit; form is a difference and gets its own panel.
 */
export default function LoadProjection({ projection, goal }) {
  const data = projectionData(projection);
  if (data.length < 8 || !projection?.projection?.length) return null;
  const today = projection.history[projection.history.length - 1].date;
  const end = projection.projection[projection.projection.length - 1].date;
  const planned = plannedDayCount(projection);
  const low = lowestForm(projection);
  const target = goal?.target_date ? formOn(projection, goal.target_date) : null;
  const planEnd = projection.plan_through;
  const assumedFrom = planEnd && planEnd < end ? planEnd : null;

  const shared = (
    <>
      <CartesianGrid stroke="rgba(255,255,255,0.1)" strokeDasharray="3 5" vertical={false} />
      <XAxis dataKey="date" tickFormatter={fmtDay} tick={AXIS} axisLine={false} tickLine={false} minTickGap={40} />
      <ReferenceArea x1={today} x2={end} fill="#3fd0e0" fillOpacity={0.06} />
      <ReferenceLine x={today} stroke="rgba(232,241,238,0.55)" strokeDasharray="4 4" label={{ value: "today", fill: "#e8f1ee", fontSize: 11, position: "insideTopLeft" }} />
      {assumedFrom && <ReferenceLine x={assumedFrom} stroke="rgba(244,210,122,0.7)" strokeDasharray="2 4" label={{ value: "plan ends", fill: "#f4d27a", fontSize: 11, position: "insideTopRight", dy: 16 }} />}
      {goal?.target_date && goal.target_date <= end && goal.target_date > today && (
        <ReferenceLine x={goal.target_date} stroke="#8af0bd" label={{ value: goal.description.slice(0, 18), fill: "#8af0bd", fontSize: 11, position: "insideTopRight", dy: 32 }} />
      )}
    </>
  );

  return (
    <section className="card panel-dark load-projection">
      <h3>Fitness, fatigue and the next four weeks</h3>
      <p className="chart-note">
        Solid lines are what happened. Dashed lines project forward: the next {planned} {planned === 1 ? "day follows" : "days follow"} your
        saved plan{assumedFrom ? `, then your recent average of ${Math.round(projection.assumed_daily_tss)} TSS a day is assumed` : ""}.
        {low && <> The projected low point for form is <strong>{low.tsb > 0 ? "+" : ""}{low.tsb}</strong> on {fmtDay(low.date)} ({formLabel(low.tsb)}).</>}
        {target && <> On {goal.description}, form is projected at <strong>{target.tsb > 0 ? "+" : ""}{target.tsb}</strong> ({formLabel(target.tsb)}).</>}
      </p>

      <div className="lp-legend" aria-hidden="true">
        <span><i style={{ background: CYAN }} /> Fitness (CTL)</span>
        <span><i style={{ background: COPPER }} /> Fatigue (ATL)</span>
        <span><i className="dash" /> projected</span>
      </div>
      <ResponsiveContainer width="100%" height={210}>
        <ComposedChart data={data} margin={{ top: 8, right: 10, bottom: 0, left: -14 }}>
          {shared}
          <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} allowDecimals={false} domain={["auto", "auto"]} />
          <Tooltip {...TOOLTIP} labelFormatter={fmtDay} formatter={tooltipFormatter} />
          <Line type="monotone" dataKey="ctl" name={NAMES.ctl} stroke={CYAN} strokeWidth={3} dot={false} isAnimationActive={false}
                activeDot={{ r: 5, stroke: "#fff", strokeWidth: 2, fill: CYAN }} />
          <Line type="monotone" dataKey="atl" name={NAMES.atl} stroke={COPPER} strokeWidth={2} dot={false} isAnimationActive={false}
                activeDot={{ r: 4, stroke: "#fff", strokeWidth: 2, fill: COPPER }} />
          <Line type="monotone" dataKey="ctlP" name={`${NAMES.ctl} (projected)`} stroke={CYAN} strokeWidth={3} strokeDasharray="6 5" dot={false} isAnimationActive={false}
                activeDot={{ r: 5, stroke: "#fff", strokeWidth: 2, fill: CYAN }} />
          <Line type="monotone" dataKey="atlP" name={`${NAMES.atl} (projected)`} stroke={COPPER} strokeWidth={2} strokeDasharray="6 5" dot={false} isAnimationActive={false}
                activeDot={{ r: 4, stroke: "#fff", strokeWidth: 2, fill: COPPER }} />
        </ComposedChart>
      </ResponsiveContainer>

      <div className="lp-legend" aria-hidden="true">
        <span><i style={{ background: GREEN }} /> Form (TSB = fitness − fatigue)</span>
        <span className="lp-zone">below −30: deep fatigue · −30 to −10: building · −10 to +5: balanced · above +5: fresh</span>
      </div>
      <ResponsiveContainer width="100%" height={150}>
        <ComposedChart data={data} margin={{ top: 8, right: 10, bottom: 0, left: -14 }}>
          {shared}
          <YAxis tick={AXIS} axisLine={false} tickLine={false} width={44} allowDecimals={false} domain={["auto", "auto"]} />
          <ReferenceLine y={0} stroke="rgba(232,241,238,0.45)" />
          <ReferenceArea y1={-30} y2={-200} fill="#e58a4a" fillOpacity={0.12} />
          <Tooltip {...TOOLTIP} labelFormatter={fmtDay} formatter={tooltipFormatter} />
          <Area type="monotone" dataKey="tsb" name={NAMES.tsb} stroke={GREEN} strokeWidth={2.5} fill={GREEN} fillOpacity={0.12} dot={false} isAnimationActive={false}
                activeDot={{ r: 4, stroke: "#fff", strokeWidth: 2, fill: GREEN }} />
          <Area type="monotone" dataKey="tsbP" name={`${NAMES.tsb} (projected)`} stroke={GREEN} strokeWidth={2.5} strokeDasharray="6 5" fill={GREEN} fillOpacity={0.06} dot={false} isAnimationActive={false}
                activeDot={{ r: 4, stroke: "#fff", strokeWidth: 2, fill: GREEN }} />
        </ComposedChart>
      </ResponsiveContainer>
    </section>
  );
}
