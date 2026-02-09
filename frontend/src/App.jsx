import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import WorkoutCalendar from "./pages/WorkoutCalendar";
import WorkoutImport from "./pages/WorkoutImport";
import WeeklyCoaching from "./pages/WeeklyCoaching";
import Dashboard from "./pages/Dashboard";
import "./styles/App.css";
import "./styles/pages.css";

function App() {
  return (
    <Router>
      <AppLayout>
        <Routes>
          <Route path="/" element={<WorkoutCalendar />} />
          <Route path="/calendar" element={<WorkoutCalendar />} />
          <Route path="/import" element={<WorkoutImport />} />
          <Route path="/coaching" element={<WeeklyCoaching />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </AppLayout>
    </Router>
  );
}

export default App;
