import React from "react";
import { Calendar as CalendarIcon } from "lucide-react";

function WorkoutCalendar() {
  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-title">
          <CalendarIcon size={32} />
          <h1>Workout Calendar</h1>
        </div>
        <p className="page-subtitle">
          View and manage your weekly training schedule
        </p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Coming Soon</h2>
        </div>
        <p>This page will display your workout calendar with:</p>
        <ul>
          <li>Weekly calendar grid navigation</li>
          <li>Planned vs completed workout tracking</li>
          <li>Routine workout display with rep/weight tracking</li>
          <li>Bike/run workout display with interval visualization</li>
          <li>Working timer for timed workouts</li>
        </ul>
      </div>
    </div>
  );
}

export default WorkoutCalendar;
