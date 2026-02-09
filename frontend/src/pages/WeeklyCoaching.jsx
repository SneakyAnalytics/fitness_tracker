import React from "react";
import { Brain } from "lucide-react";

function WeeklyCoaching() {
  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <Brain size={32} />
          <h1>Weekly Coaching</h1>
        </div>
        <p className="page-subtitle">
          AI-powered weekly analysis and workout planning
        </p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Coming Soon</h2>
        </div>
        <p>This page will provide:</p>
        <ul>
          <li>Week selection (Mon-Sun completed training)</li>
          <li>Context inputs (schedule, goals, feedback, soreness)</li>
          <li>Two-step AI workflow: Analysis → Workout Plan</li>
          <li>Cost tracking for API usage</li>
          <li>Automatic Zwift file generation</li>
        </ul>
      </div>
    </div>
  );
}

export default WeeklyCoaching;
