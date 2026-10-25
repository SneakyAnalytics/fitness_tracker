import React from "react";
import badge from "../assets/coach-badge.webp";
import board from "../assets/coach-board.webp";
import calendar from "../assets/coach-calendar.webp";
import dashboard from "../assets/coach-dashboard.webp";

/**
 * Coach Claude's artwork: one badge per section, all transparent-background images
 * in a square box (object-fit: contain) so they drop in where an icon goes.
 *   CoachBadge      robot with a whistle on a cord (app logo)
 *   CoachBoard      the coach studying a holographic tactics board (Weekly Coaching)
 *   CoachCalendar   "Calendar Strategist" (Workout Calendar)
 *   CoachDashboard  the dashboard badge (Training Dashboard)
 */
function Art({ src, size, className, ...rest }) {
  return <img src={src} alt="" height={size} style={{ height: size, width: size, objectFit: "contain" }} className={className} {...rest} />;
}

export const CoachBadge = (props) => <Art src={badge} size={48} {...props} />;
export const CoachBoard = (props) => <Art src={board} size={32} {...props} />;
export const CoachCalendar = (props) => <Art src={calendar} size={32} {...props} />;
export const CoachDashboard = (props) => <Art src={dashboard} size={32} {...props} />;

export default CoachBadge;
