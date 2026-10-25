import React from "react";
import { Cloud, CloudFog, CloudLightning, CloudRain, CloudSnow, CloudSun, Droplets, Sun } from "lucide-react";
import { describeWeather, isWet } from "../lib/weather";
import "./WeatherChip.css";

const ICONS = { sun: Sun, "cloud-sun": CloudSun, cloud: Cloud, fog: CloudFog, rain: CloudRain, snow: CloudSnow, storm: CloudLightning };

/** One day's forecast: icon, high/low and the chance of rain. Wet days are tinted. */
export default function WeatherChip({ day }) {
  if (!day) return null;
  const { label, icon } = describeWeather(day.code);
  const Icon = ICONS[icon] || Cloud;
  return (
    <div className={`weather-chip ${isWet(day) ? "wet" : ""}`} title={`${label} · ${day.rain_pct ?? 0}% chance of rain`}>
      <Icon size={16} />
      <span className="weather-temps">
        {Math.round(day.high)}°<span className="weather-low">/{Math.round(day.low)}°</span>
      </span>
      {day.rain_pct >= 20 && (
        <span className="weather-rain">
          <Droplets size={11} />
          {day.rain_pct}%
        </span>
      )}
    </div>
  );
}
