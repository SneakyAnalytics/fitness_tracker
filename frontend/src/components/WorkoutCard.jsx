import React from "react";
import { Bike, Footprints, Dumbbell, Activity, Clock, Zap } from "lucide-react";
import "./WorkoutCard.css";

function WorkoutCard({ workout, onClick, isSelected }) {
  const getWorkoutIcon = (type) => {
    const typeLC = type?.toLowerCase() || "";
    if (typeLC.includes("bike") || typeLC.includes("cycling")) return Bike;
    if (typeLC.includes("run")) return Footprints;
    if (typeLC.includes("strength") || typeLC.includes("routine"))
      return Dumbbell;
    return Activity;
  };

  const getWorkoutBadgeClass = (type) => {
    const typeLC = type?.toLowerCase() || "";
    if (typeLC.includes("bike") || typeLC.includes("cycling"))
      return "badge-cycling";
    if (typeLC.includes("run")) return "badge-running";
    if (typeLC.includes("strength") || typeLC.includes("routine"))
      return "badge-strength";
    return "badge-other";
  };

  const Icon = getWorkoutIcon(workout.type);
  const badgeClass = getWorkoutBadgeClass(workout.type);

  return (
    <div
      className={`workout-card ${isSelected ? "selected" : ""} ${workout.completed ? "completed" : "planned"}`}
      onClick={onClick}
    >
      <div className="workout-card-header">
        <div className={`badge ${badgeClass}`}>
          <Icon size={14} />
          <span>{workout.type}</span>
        </div>
        {workout.completed && (
          <span className="completed-badge">✓ Completed</span>
        )}
      </div>

      <h4 className="workout-title">
        {workout.name || workout.title || "Workout"}
      </h4>

      <div className="workout-stats">
        {workout.duration && (
          <div className="stat">
            <Clock size={14} />
            <span>{formatDuration(workout.duration)}</span>
          </div>
        )}
        {workout.tss && (
          <div className="stat">
            <Zap size={14} />
            <span>{workout.tss} TSS</span>
          </div>
        )}
      </div>

      {workout.description && (
        <p className="workout-description">{workout.description}</p>
      )}
    </div>
  );
}

function formatDuration(seconds) {
  if (!seconds) return "";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  if (hours > 0) {
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
  return `${minutes}m`;
}

export default WorkoutCard;
