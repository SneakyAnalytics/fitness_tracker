import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Calendar, Brain, BarChart3, Menu, X, Wrench } from "lucide-react";
import UserProfile from "./UserProfile";
import "./AppLayout.css";

function AppLayout({ children }) {
  const isNarrow = () => window.matchMedia("(max-width: 768px)").matches;
  const [sidebarOpen, setSidebarOpen] = useState(() => !isNarrow());
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { path: "/calendar", icon: Calendar, label: "Workout Calendar" },
    { path: "/coaching", icon: Brain, label: "Weekly Coaching" },
    { path: "/dashboard", icon: BarChart3, label: "Dashboard" },
  ];
  // Import, matching and analysis stay in the Streamlit admin app.
  const adminUrl = import.meta.env.VITE_ADMIN_URL || `${window.location.protocol}//${window.location.hostname}:8501`;

  const isActive = (path) => location.pathname === path;

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-header gradient-forest">
          <Brain className="sidebar-logo" size={32} />
          <h1 className="sidebar-title">Coach Claude</h1>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(({ path, icon: Icon, label }) => (
            <button
              key={path}
              onClick={() => {
                navigate(path);
                if (isNarrow()) setSidebarOpen(false);
              }}
              className={`nav-item ${isActive(path) ? "active" : ""}`}
            >
              <Icon size={20} />
              <span className="nav-label">{label}</span>
            </button>
          ))}
          <a className="nav-item" href={adminUrl} target="_blank" rel="noopener noreferrer">
            <Wrench size={20} />
            <span className="nav-label">Admin (import &amp; matching)</span>
          </a>
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
