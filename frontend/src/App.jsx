import React, { lazy, Suspense } from "react";
import { BrowserRouter as Router, Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import WorkoutCalendar from "./pages/WorkoutCalendar";
// Chart-heavy pages load on demand so the calendar opens fast on a phone.
const WeeklyCoaching = lazy(() => import("./pages/WeeklyCoaching"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
import "./styles/App.css";
import "./styles/pages.css";

function App() {
  return (
    <Router>
      <AppLayout>
        <Suspense fallback={<div className="spinner">Loading…</div>}>
        <Routes>
          <Route path="/" element={<Navigate to="/calendar" replace />} />
          <Route path="/calendar" element={<WorkoutCalendar />} />
          <Route path="/coaching" element={<WeeklyCoaching />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="*" element={<Navigate to="/calendar" replace />} />
        </Routes>
        </Suspense>
      </AppLayout>
    </Router>
  );
}

export default App;
