import React from "react";
import { Upload } from "lucide-react";

function WorkoutImport() {
  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <Upload size={32} />
          <h1>Workout Import & Analysis</h1>
        </div>
        <p className="page-subtitle">
          Sync from TrainingPeaks and match workouts
        </p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Coming Soon</h2>
        </div>
        <p>This page will handle:</p>
        <ul>
          <li>TrainingPeaks sync with date range selection</li>
          <li>Manual workout matching (proposed ↔ completed)</li>
          <li>Re-matching existing workouts</li>
          <li>FIT file assignment management</li>
        </ul>
      </div>
    </div>
  );
}

export default WorkoutImport;
