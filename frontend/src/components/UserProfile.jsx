import React, { useState, useEffect } from "react";
import { User, Settings } from "lucide-react";
import { athleteAPI } from "../api/client";
import "./UserProfile.css";

function UserProfile() {
  const [showSettings, setShowSettings] = useState(false);
  const [athleteSettings, setAthleteSettings] = useState({
    ftp: "",
    hr_zones: "",
    power_zones: "",
  });
  const [loading, setLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await athleteAPI.getSettings();
      if (response.data) {
        setAthleteSettings({
          ftp: response.data.ftp || "",
          hr_zones: response.data.hr_zones || "",
          power_zones: response.data.power_zones || "",
        });
      }
    } catch (error) {
      console.error("Failed to load athlete settings:", error);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setSaveStatus("");
    try {
      await athleteAPI.saveSettings(athleteSettings);
      setSaveStatus("Settings saved successfully!");
      setTimeout(() => setSaveStatus(""), 3000);
    } catch (error) {
      setSaveStatus("Failed to save settings");
      console.error("Error saving settings:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="user-profile">
      <button
        className="profile-button"
        onClick={() => setShowSettings(!showSettings)}
      >
        <User size={20} />
        <span>Athlete</span>
      </button>

      {showSettings && (
        <>
          <div
            className="settings-overlay"
            onClick={() => setShowSettings(false)}
          />
          <div className="settings-panel">
            <div className="settings-header">
              <Settings size={20} />
              <h3>Athlete Settings</h3>
            </div>

            <div className="settings-content">
              <div className="form-group">
                <label htmlFor="ftp">FTP (Watts)</label>
                <input
                  id="ftp"
                  type="number"
                  className="input"
                  value={athleteSettings.ftp}
                  onChange={(e) =>
                    setAthleteSettings({
                      ...athleteSettings,
                      ftp: e.target.value,
                    })
                  }
                  placeholder="e.g., 250"
                />
              </div>

              <div className="form-group">
                <label htmlFor="hr_zones">Heart Rate Zones</label>
                <input
                  id="hr_zones"
                  type="text"
                  className="input"
                  value={athleteSettings.hr_zones}
                  onChange={(e) =>
                    setAthleteSettings({
                      ...athleteSettings,
                      hr_zones: e.target.value,
                    })
                  }
                  placeholder="e.g., 120,140,160,170,180"
                />
                <small className="input-hint">Comma-separated values</small>
              </div>

              <div className="form-group">
                <label htmlFor="power_zones">Power Zones (Watts)</label>
                <input
                  id="power_zones"
                  type="text"
                  className="input"
                  value={athleteSettings.power_zones}
                  onChange={(e) =>
                    setAthleteSettings({
                      ...athleteSettings,
                      power_zones: e.target.value,
                    })
                  }
                  placeholder="e.g., 150,180,210,240,270"
                />
                <small className="input-hint">Comma-separated values</small>
              </div>

              {saveStatus && (
                <div
                  className={`save-status ${saveStatus.includes("success") ? "success" : "error"}`}
                >
                  {saveStatus}
                </div>
              )}

              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={loading}
              >
                {loading ? "Saving..." : "Save Settings"}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default UserProfile;
