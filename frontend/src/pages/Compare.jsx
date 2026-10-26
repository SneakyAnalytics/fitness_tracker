import React, { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format, parseISO } from "date-fns";
import { compareAPI } from "../api/client";
import { CoachDashboard } from "../components/CoachLogo";
import { defaultPair, intervalRows, mergeSeries, similarTo, summaryRows } from "../lib/compare";
import "../styles/pages.css";
import "./Compare.css";

const A_COLOR = "#3fd0e0";
const B_COLOR = "#e58a4a";
const AXIS = { fill: "rgba(232, 241, 238, 0.7)", fontSize: 11 };
const TOOLTIP = {
  contentStyle: { background: "#0e1d2c", border: "1px solid rgba(63,208,224,0.45)", borderRadius: 8, color: "#e8f1ee" },
  labelStyle: { color: "#8be3ee", fontWeight: 600 },
  itemStyle: { color: "#e8f1ee" },
};
const label = (r) => `${format(parseISO(r.date), "EEE MMM d")} · ${r.name}${r.tss != null ? ` · ${Math.round(r.tss)} TSS` : ""}`;

function useRide(id) {
  return useQuery({ queryKey: ["compare-ride", id], enabled: !!id, queryFn: async () => (await compareAPI.ride(id)).data, staleTime: 5 * 60 * 1000 });
}

function Picker({ name, color, value, rides, onChange }) {
  return (
    <label className="cmp-picker">
      <span><i style={{ background: color }} /> {name}</span>
      <select className="input" value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
        <option value="">Choose a ride…</option>
        {rides.map((r) => <option key={r.id} value={r.id}>{label(r)}</option>)}
      </select>
    </label>
  );
}

function SeriesChart({ rows, aKey, bKey, unit, height }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={rows} margin={{ top: 8, right: 10, bottom: 0, left: -10 }}>
        <CartesianGrid stroke="rgba(255,255,255,0.1)" strokeDasharray="3 5" vertical={false} />
        <XAxis dataKey="min" type="number" domain={[0, "dataMax"]} tick={AXIS} axisLine={false} tickLine={false}
               tickFormatter={(m) => `${Math.round(m)}m`} allowDecimals={false} />
        <YAxis tick={AXIS} axisLine={false} tickLine={false} width={46} allowDecimals={false} domain={["auto", "auto"]} />
        <Tooltip {...TOOLTIP} labelFormatter={(m) => `${Math.round(m * 10) / 10} min`} formatter={(v, n) => [`${v} ${unit}`, n]} />
        <Line type="monotone" dataKey={aKey} name="Ride A" stroke={A_COLOR} strokeWidth={2.5} dot={false} connectNulls isAnimationActive={false}
              activeDot={{ r: 4, stroke: "#fff", strokeWidth: 2, fill: A_COLOR }} />
        <Line type="monotone" dataKey={bKey} name="Ride B" stroke={B_COLOR} strokeWidth={2.5} dot={false} connectNulls isAnimationActive={false}
              activeDot={{ r: 4, stroke: "#fff", strokeWidth: 2, fill: B_COLOR }} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

const watts = (i) => (i?.actual_avg_w != null ? `${Math.round(i.actual_avg_w)} W` : "–");
const signed = (n) => (n == null ? "–" : `${n > 0 ? "+" : ""}${n}`);

function Compare() {
  const [params, setParams] = useSearchParams();
  const { data: rides = [], isLoading } = useQuery({ queryKey: ["compare-rides"], queryFn: async () => (await compareAPI.rides()).data.rides });
  const a = params.get("a");
  const b = params.get("b");

  // First visit: the newest ride against its previous like-for-like.
  useEffect(() => {
    if (!rides.length || (a && b)) return;
    if (a) {   // arrived from a workout: pick its natural comparison
      const y = similarTo(rides, a);
      if (y) setParams({ a, b: y }, { replace: true });
      return;
    }
    if (b) return;
    const [x, y] = defaultPair(rides);
    setParams({ ...(x ? { a: x } : {}), ...(y ? { b: y } : {}) }, { replace: true });
  }, [rides, a, b, setParams]);

  const set = (key) => (value) => setParams((p) => { const q = new URLSearchParams(p); value ? q.set(key, value) : q.delete(key); return q; }, { replace: true });
  const ra = useRide(a);
  const rb = useRide(b);
  const rowsData = ra.data || rb.data ? mergeSeries(ra.data, rb.data) : [];
  const summary = ra.data && rb.data ? summaryRows(ra.data, rb.data) : [];
  const intervals = ra.data && rb.data ? intervalRows(ra.data, rb.data).filter((r) => r.a || r.b) : [];
  const hasHr = rowsData.some((r) => r.aHr != null || r.bHr != null);

  return (
    <div className="page-container compare-page">
      <div className="page-header">
        <div className="hero-title">
          <CoachDashboard size={96} />
          <div>
            <h1 className="page-title">Compare rides</h1>
            <p className="header-subtitle">Overlay two rides to see whether the same session is getting easier.</p>
          </div>
        </div>
      </div>

      <div className="card cmp-pickers">
        <Picker name="Ride A" color={A_COLOR} value={a} rides={rides} onChange={set("a")} />
        <Picker name="Ride B" color={B_COLOR} value={b} rides={rides} onChange={set("b")} />
      </div>
      {isLoading && <p className="cmp-note">Loading rides…</p>}
      {(ra.isError || rb.isError) && <p className="cmp-error">Could not load one of the rides.</p>}

      {rowsData.length > 0 && (
        <section className="card panel-dark">
          <h3>Power (30-second average)</h3>
          <div className="cmp-legend" aria-hidden="true">
            <span><i style={{ background: A_COLOR, height: 3, width: 18, display: "inline-block" }} /> Ride A</span>
            <span><i style={{ background: B_COLOR, height: 3, width: 18, display: "inline-block" }} /> Ride B</span>
          </div>
          <SeriesChart rows={rowsData} aKey="a" bKey="b" unit="W" height={240} />
          {hasHr && (
            <>
              <h3 className="cmp-h3">Heart rate</h3>
              <SeriesChart rows={rowsData} aKey="aHr" bKey="bHr" unit="bpm" height={160} />
            </>
          )}
        </section>
      )}

      {summary.length > 0 && (
        <section className="card cmp-summary">
          <h3>Side by side</h3>
          <div className="cmp-scroll">
            <table className="cmp-table">
              <thead><tr><th /><th><i style={{ background: A_COLOR }} /> A</th><th><i style={{ background: B_COLOR }} /> B</th><th>A − B</th></tr></thead>
              <tbody>
                {summary.map((r) => (
                  <tr key={r.label}>
                    <td>{r.label}</td>
                    <td>{r.a ?? "–"} {r.a != null && r.unit}</td>
                    <td>{r.b ?? "–"} {r.b != null && r.unit}</td>
                    <td className="delta">{signed(r.delta)} {r.delta != null && r.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {intervals.length > 0 && (
        <section className="card cmp-summary">
          <h3>Intervals</h3>
          <p className="cmp-note">Average power of each prescribed block, matched by position. Higher at the same target means the block is getting easier.</p>
          <div className="cmp-scroll">
            <table className="cmp-table">
              <thead><tr><th>#</th><th>Block</th><th>Target</th><th><i style={{ background: A_COLOR }} /> A</th><th><i style={{ background: B_COLOR }} /> B</th></tr></thead>
              <tbody>
                {intervals.map((r) => {
                  const t = r.a || r.b;
                  const target = t.target_low_w != null ? (t.target_high_w && t.target_high_w !== t.target_low_w ? `${Math.round(t.target_low_w)}-${Math.round(t.target_high_w)} W` : `${Math.round(t.target_low_w)} W`) : "–";
                  return <tr key={r.index}><td>{r.index}</td><td>{r.name}</td><td>{target}</td><td>{watts(r.a)}</td><td>{watts(r.b)}</td></tr>;
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {!isLoading && rides.length === 0 && <p className="cmp-note">No rides with a ride file yet.</p>}
    </div>
  );
}

export default Compare;
