import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { CoachDashboard } from "../components/CoachLogo";
import { METRICS } from "../lib/metrics";
import "../styles/pages.css";
import "./MetricGuide.css";

/** One section per metric, anchored by id so tiles can link straight to theirs (/metrics#tsb). */
function MetricGuide() {
  const { hash } = useLocation();
  const target = hash.replace("#", "");

  useEffect(() => {
    if (!target) return;
    document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [target]);

  return (
    <div className="page-container metric-guide">
      <div className="page-header">
        <Link to="/dashboard" className="back-link">
          <ArrowLeft size={16} /> Dashboard
        </Link>
        <div className="hero-title">
          <CoachDashboard size={96} />
          <div>
            <h1 className="page-title">Metric guide</h1>
            <p className="header-subtitle">What every number means, how it is calculated here, and how Coach Claude uses it.</p>
          </div>
        </div>
      </div>

      <nav className="guide-index" aria-label="Metrics">
        {METRICS.map((m) => (
          <a key={m.id} href={`#${m.id}`} className={m.id === target ? "active" : ""}>
            {m.name.replace(/ \(.*\)/, "")}
          </a>
        ))}
      </nav>

      {METRICS.map((m) => (
        <section key={m.id} id={m.id} className={`card guide-card ${m.id === target ? "targeted" : ""}`}>
          <h2>{m.name}</h2>
          <p className="guide-lead">{m.what}</p>
          <div className="guide-grid">
            <div>
              <h3>How it's calculated</h3>
              <p>{m.how}</p>
              <h3>What Coach Claude does with it</h3>
              <p>{m.coach}</p>
              <h3>Keep in mind</h3>
              <p>{m.limits}</p>
            </div>
            <div>
              <h3>How to read it</h3>
              <table className="guide-ranges">
                <tbody>
                  {m.ranges.map(([range, meaning]) => (
                    <tr key={range}>
                      <th scope="row">{range}</th>
                      <td>{meaning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}

export default MetricGuide;
