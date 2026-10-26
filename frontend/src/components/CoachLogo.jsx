import React from "react";
import badge from "../assets/coach-badge.webp";
import board from "../assets/coach-board.webp";
import calendar from "../assets/coach-calendar.webp";
import dashboard from "../assets/coach-dashboard.webp";
import admin from "../assets/coach-admin.webp";
import artCycling from "../assets/art-cycling.webp";
import artRun from "../assets/art-run.webp";
import artStrength from "../assets/art-strength.webp";
import artMobility from "../assets/art-mobility.webp";
import artSauna from "../assets/art-sauna.webp";
import artRest from "../assets/art-rest.webp";
import typeThreshold from "../assets/type-threshold.webp";
import typeSweetSpot from "../assets/type-sweet-spot.webp";
import typeOverUnder from "../assets/type-over-under.webp";
import typeVo2 from "../assets/type-vo2max.webp";
import typeTempo from "../assets/type-tempo.webp";
import typeEndurance from "../assets/type-endurance.webp";
import wave from "../assets/coach-wave.webp";
import errorArt from "../assets/coach-error.webp";

/**
 * Coach Claude's artwork: one badge per section, all transparent-background images
 * in a square box (object-fit: contain) so they drop in where an icon goes.
 *   CoachBadge      robot with a whistle on a cord (app logo)
 *   CoachBoard      the coach studying a holographic tactics board (Weekly Coaching)
 *   CoachCalendar   "Calendar Strategist" (Workout Calendar)
 *   CoachDashboard  the dashboard badge (Training Dashboard)
 *   CoachAdmin      the admin badge (problems, ride files, goals)
 */
function Art({ src, size, className, ...rest }) {
  return <img src={src} alt="" height={size} style={{ height: size, width: size, objectFit: "contain" }} className={className} {...rest} />;
}

export const CoachBadge = (props) => <Art src={badge} size={48} {...props} />;
export const CoachBoard = (props) => <Art src={board} size={32} {...props} />;
export const CoachCalendar = (props) => <Art src={calendar} size={32} {...props} />;
export const CoachDashboard = (props) => <Art src={dashboard} size={32} {...props} />;

export const CoachAdmin = (props) => <Art src={admin} size={32} {...props} />;

export const CoachWave = (props) => <Art src={wave} size={140} {...props} />;
export const CoachError = (props) => <Art src={errorArt} size={96} {...props} />;

const SESSION_ART = {
  cycling: artCycling, run: artRun, strength: artStrength, mobility: artMobility, sauna: artSauna, rest: artRest,
  threshold: typeThreshold, sweet_spot: typeSweetSpot, over_under: typeOverUnder, vo2max: typeVo2, tempo: typeTempo, endurance: typeEndurance,
};

/** Key-session badge for a ride, by name; the same order as the backend's classification (progression.py). */
export function bikeArtKey(name) {
  const n = (name || "").toLowerCase();
  if (/(commute|active recovery|recovery spin|flush|easy spin|recovery ride)/.test(n)) return "cycling";
  if (/(vo2|vo₂)/.test(n)) return "vo2max";
  if (/(over[-/ ]?unders?|overs\/unders)/.test(n)) return "over_under";
  if (/sweet ?spot/.test(n)) return "sweet_spot";
  if (/(threshold|ftp interval|pyramid)/.test(n)) return "threshold";
  if (/tempo/.test(n)) return "tempo";
  if (/(endurance|zone 2|\bz2\b|aerobic|long ride|\bbase\b)/.test(n)) return "endurance";
  return "cycling";
}

/** Which session badge fits a workout, or null when there isn't one (hiking, walking...). */
export function sessionArtKey(type, name) {
  const t = (type || "").toLowerCase();
  const n = (name || "").toLowerCase();
  if (n.includes("sauna") || n.includes("hot bath")) return "sauna";
  if (n.includes("rest day") || t === "rest") return "rest";
  if (t.includes("bike") || t.includes("cycling")) return bikeArtKey(n);
  if (t.includes("run")) return "run";
  if (t.includes("strength") || t.includes("routine")) return "strength";
  if (t.includes("yoga") || t.includes("mobility")) return "mobility";
  if (/(yoga|mobility|stretch|hip |reset|flow)/.test(n)) return "mobility";
  return null;
}

export function SessionArt({ type, name, size = 30, ...rest }) {
  const key = sessionArtKey(type, name);
  return key ? <Art src={SESSION_ART[key]} size={size} {...rest} /> : null;
}

/** The coach's face in the chat; while it is answering, rings pulse and the badge rocks like a whistle being blown. */
export function CoachAvatar({ speaking = false, size = 44 }) {
  return (
    <span className={`coach-avatar ${speaking ? "speaking" : ""}`} style={{ width: size, height: size }}>
      <Art src={badge} size={size} />
    </span>
  );
}

/** A session badge by its art name: cycling, run, strength, mobility, sauna or rest. */
export function ArtByKey({ name, size = 30, ...rest }) {
  return SESSION_ART[name] ? <Art src={SESSION_ART[name]} size={size} {...rest} /> : null;
}

export default CoachBadge;
