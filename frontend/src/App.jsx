import React, { lazy, Suspense } from "react";
import { BrowserRouter as Router, Navigate, Route, Routes, useLocation } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import PlanPrint from "./pages/PlanPrint";
import WorkoutCalendar from "./pages/WorkoutCalendar";
import Today from "./pages/Today";
// Chart-heavy pages load on demand so the calendar opens fast on a phone.
const WeeklyCoaching = lazy(() => import("./pages/WeeklyCoaching"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const MetricGuide = lazy(() => import("./pages/MetricGuide"));
const Admin = lazy(() => import("./pages/Admin"));
import "./styles/App.css";
import "./styles/pages.css";

// Each page slides in softly; keyed on the path so the animation replays on every tab change.
function Pages() {
  const { pathname } = useLocation();
  return (
    <div key={pathname} className="page-transition">
      <Routes>
        <Route path="/" element={<Today />} />
        <Route path="/calendar" element={<WorkoutCalendar />} />
        <Route path="/coaching" element={<WeeklyCoaching />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="/metrics" element={<MetricGuide />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        {/* the print view is a bare page: no sidebar or top bar */}
        <Route path="/print" element={<PlanPrint />} />
        <Route
          path="*"
          element={
            <AppLayout>
              <Suspense fallback={<div className="spinner">Loading…</div>}>
                <Pages />
              </Suspense>
            </AppLayout>
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
