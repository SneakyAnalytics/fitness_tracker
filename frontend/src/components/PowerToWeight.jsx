import React from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format, parseISO } from "date-fns";
import { weightChange, wkgProgress } from "../lib/powerToWeight";
import "./PowerToWeight.css";

const GREEN = "#8af0bd";

/** FTP divided by weight (the average of the latest week of scale readings), with progress toward the W/kg goal. */
export default function PowerToWeight({ data }) {
  const progress = wkgProgress(data);
  if (!progress) return null;
  const change = weightChange(data);
  return (
    <section className="card panel-dark power-to-weight">
      <div className="ptw-main">
        <span className="ptw-label">Power-to-weight</span>
        <div className="ptw-number">{data.wkg.toFixed(2)}<small> W/kg</small></div>
        <p className="ptw-sub">{data.ftp} W at {data.weight_kg} kg (average of the week to {format(parseISO(data.weight_date), "MMM d")})</p>
        {progress.pct != null && (
          <div className="ptw-bar" role="progressbar" aria-valuenow={progress.pct} aria-valuemin={0} aria-valuemax={100}
               aria-label={`${progress.pct}% of the ${data.target} W/kg target`}>
            <span className={progress.reached ? "done" : ""} style={{ width: `${progress.pct}%` }} />
          </div>
        )}
        {progress.sentence && <p className="ptw-sentence">{progress.sentence}</p>}
      </div>
      {data.weekly?.length > 2 && (
        <div className="ptw-trend">
          <span className="ptw-label">Weight, weekly average{change != null ? ` (${change > 0 ? "+" : ""}${change} kg)` : ""}</span>
          <ResponsiveContainer width="100%" height={90}>
            <AreaChart data={data.weekly} margin={{ top: 6, right: 4, bottom: 0, left: 4 }}>
              <XAxis dataKey="week_start" hide />
              <YAxis hide domain={["dataMin - 1", "dataMax + 1"]} />
              <Tooltip
                contentStyle={{ background: "#0e1d2c", border: "1px solid rgba(63,208,224,0.45)", borderRadius: 8, color: "#e8f1ee" }}
                labelStyle={{ color: "#8be3ee", fontWeight: 600 }} itemStyle={{ color: "#e8f1ee" }}
                labelFormatter={(d) => `Week of ${format(parseISO(d), "MMM d")}`} formatter={(v) => [`${v} kg`, "Average"]}
              />
              <Area type="monotone" dataKey="kg" stroke={GREEN} strokeWidth={2.5} fill={GREEN} fillOpacity={0.15} dot={false} isAnimationActive={false}
                    activeDot={{ r: 4, stroke: "#fff", strokeWidth: 2, fill: GREEN }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
