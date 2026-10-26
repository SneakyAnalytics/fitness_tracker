import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Menu, Moon, Sun, Volume2, VolumeX, X } from "lucide-react";
import { CoachAdmin, CoachBadge, CoachBoard, CoachCalendar, CoachDashboard } from "./CoachLogo";
import UserProfile from "./UserProfile";
import { applyTheme } from "../lib/theme";
import { isMuted, setMuted } from "../lib/sounds";
import "./AppLayout.css";

function AppLayout({ children }) {
  const isNarrow = () => window.matchMedia("(max-width: 768px)").matches;
  const [sidebarOpen, setSidebarOpen] = useState(() => !isNarrow());
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || "light");
  const [muted, setMutedState] = useState(isMuted);
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { path: "/calendar", icon: CoachCalendar, label: "Workout Calendar" },
    { path: "/coaching", icon: CoachBoard, label: "Weekly Coaching" },
    { path: "/dashboard", icon: CoachDashboard, label: "Dashboard" },
    { path: "/admin", icon: CoachAdmin, label: "Admin" },
  ];

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    applyTheme(next);
    setTheme(next);
  };
  const toggleMute = () => {
    setMuted(!muted);
    setMutedState(!muted);
  };

  const isActive = (path) => location.pathname === path;

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-header gradient-forest">
          <CoachBadge className="sidebar-logo" size={48} />
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
              <Icon size={30} />
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

          <div className="top-bar-actions">
            <button className="icon-toggle" onClick={toggleMute} aria-label={muted ? "Unmute sounds" : "Mute sounds"}
                    title={muted ? "Sounds off" : "Sounds on"}>
              {muted ? <VolumeX size={20} /> : <Volume2 size={20} />}
            </button>
            <button className="icon-toggle" onClick={toggleTheme} aria-label="Switch light or dark theme"
                    title={theme === "dark" ? "Switch to light" : "Switch to dark"}>
              {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <UserProfile />
          </div>
        </header>

        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}

export default AppLayout;
