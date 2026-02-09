import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Calendar,
  Upload,
  Brain,
  BarChart3,
  Menu,
  X,
  Mountain,
} from "lucide-react";
import UserProfile from "./UserProfile";
import "./AppLayout.css";

function AppLayout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { path: "/calendar", icon: Calendar, label: "Workout Calendar" },
    { path: "/import", icon: Upload, label: "Import & Analysis" },
    { path: "/coaching", icon: Brain, label: "Weekly Coaching" },
    { path: "/dashboard", icon: BarChart3, label: "Analytics Dashboard" },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-header gradient-forest">
          <Mountain className="sidebar-logo" size={32} />
          <h1 className="sidebar-title">PNW Fitness</h1>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(({ path, icon: Icon, label }) => (
            <button
              key={path}
              onClick={() => navigate(path)}
              className={`nav-item ${isActive(path) ? "active" : ""}`}
            >
              <Icon size={20} />
              <span className="nav-label">{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <p className="footer-text">Born in the Pacific Northwest</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-wrapper">
        <header className="top-bar">
          <button
            className="menu-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>

          <UserProfile />
        </header>

        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}

export default AppLayout;
