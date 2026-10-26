import React from "react";
import { ArtByKey } from "./CoachLogo";
import { todaysCall } from "../lib/readiness";

/** The day's training call from readiness flags and form (TSB), on a dark instrument panel. */
export default function TodaysCall({ load, readiness }) {
  const call = todaysCall({ tsb: load?.tsb, flags: readiness?.flags || [] });
  return (
    <div className={`card panel-dark todays-call ${call.state}`}>
      <ArtByKey name={call.art} size={104} />
      <div>
        <span className="call-label">Today's call</span>
        <h3 className="call-headline">{call.headline}</h3>
        <ul className="call-reasons">
          {call.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
