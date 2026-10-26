import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Info } from "lucide-react";
import { metricById } from "../lib/metrics";
import "./MetricTile.css";

/**
 * A KPI tile whose hover (or focus, or tap) card explains the number, reads today's value in plain
 * language, and links to the full write-up on the metric guide page.
 */
export default function MetricTile({ metricId, label, value, raw, sub, ctx, action }) {
  const metric = metricById(metricId);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const cardRef = useRef(null);
  const [shift, setShift] = useState(0);

  // keep the card inside the viewport whichever column the tile is in
  useLayoutEffect(() => {
    if (!open || !cardRef.current) return;
    setShift(0);
    const r = cardRef.current.getBoundingClientRect();
    const margin = 12;
    if (r.left < margin) setShift(margin - r.left);
    else if (r.right > window.innerWidth - margin) setShift(window.innerWidth - margin - r.right);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    const onDown = (e) => wrapRef.current && !wrapRef.current.contains(e.target) && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open]);

  const reading = metric?.interpret?.(raw ?? null, ctx);

  return (
    <div
      className="metric-wrap"
      ref={wrapRef}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={(e) => !wrapRef.current.contains(e.relatedTarget) && setOpen(false)}
    >
      <button
        type="button"
        className="stat-tile card panel-dark metric-tile"
        aria-expanded={open}
        aria-describedby={metric ? `metric-card-${metricId}` : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="stat-label">
          {label}
          {metric && <Info size={12} className="metric-info" aria-hidden="true" />}
        </span>
        <span className="stat-value">{value}</span>
        {sub && <span className="stat-sub">{sub}</span>}
      </button>
      {metric && (
        <div
          id={`metric-card-${metricId}`}
          ref={cardRef}
          role="tooltip"
          className={`metric-card ${open ? "open" : ""}`}
          style={{ transform: `translateX(${shift}px)` }}
        >
          <h4>{metric.name}</h4>
          <p>{metric.short}</p>
          {reading && (
            <p className="metric-now">
              <span>Right now</span> {reading}
            </p>
          )}
          <p className="metric-read">{metric.read}</p>
          <div className="metric-links">
            <Link to={`/metrics#${metric.id}`} className="metric-more" tabIndex={open ? 0 : -1}>
              Full explanation <ArrowRight size={14} />
            </Link>
            {action && (
              <button type="button" className="metric-action" tabIndex={open ? 0 : -1} onClick={action.onClick}>
                {action.label}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
