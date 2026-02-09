import React from "react";
import { BarChart3 } from "lucide-react";

function Dashboard() {
  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <BarChart3 size={32} />
          <h1>Analytics Dashboard</h1>
        </div>
        <p className="page-subtitle">
          Comprehensive fitness analytics and progress tracking
        </p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Coming Soon</h2>
        </div>
        <p>This unified dashboard will consolidate:</p>
        <ul>
          <li>
            <strong>Daily View:</strong> Workout-by-workout timeline with AI
            analysis
          </li>
          <li>
            <strong>Progress Overview:</strong> TSS trends, training hours,
            workout distribution
          </li>
          <li>
            <strong>Personal Bests:</strong> Medal tracking for 8 effort
            durations
          </li>
          <li>
            <strong>Goals & Patterns:</strong> Active goals and coaching
            insights
          </li>
        </ul>
      </div>
    </div>
  );
}

export default Dashboard;
