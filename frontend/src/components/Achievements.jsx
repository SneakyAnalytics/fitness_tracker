import React from "react";
import { format, parseISO } from "date-fns";
import medal from "../assets/medal.webp";
import { medalLabel } from "../lib/goals";
import "./Achievements.css";

const fmt = (d) => (d ? format(parseISO(d), "MMM d, yyyy") : "");

function Medal({ goal }) {
  const label = medalLabel(goal.description);
  // a single long word ("CheddarHead") needs a smaller face so it isn't split across lines
  const tight = Math.max(...label.split(/\s+/).map((w) => w.length)) > 9;
  return (
    <li className="medal" title={goal.description}>
      <div className="medal-art">
        <img src={medal} alt="" />
        <span className={`medal-face ${tight ? "tight" : ""}`}>{label}</span>
      </div>
      <span className="medal-date">{fmt(goal.date)}</span>
    </li>
  );
}

/** Completed goals as medals, plus a countdown to the next dated target. */
export default function Achievements({ goals }) {
  const done = (goals?.completed || []).slice(0, 8);
  const next = goals?.next;
  if (done.length === 0 && !next) return null;
  return (
    <div className="card panel-dark achievements">
      <h3>Achievements</h3>
      <div className="achievements-body">
        <ul className="medal-row">
          {done.map((g) => (
            <Medal key={g.id} goal={g} />
          ))}
        </ul>
        {next && (
          <div className="next-up">
            <span className="next-label">Next target</span>
            <span className="next-days">{next.days_until === 0 ? "Today" : `${next.days_until} days`}</span>
            <span className="next-name">{medalLabel(next.description, 40)}</span>
            <span className="next-date">{fmt(next.date)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
