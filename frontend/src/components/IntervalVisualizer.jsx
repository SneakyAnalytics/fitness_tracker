import React from "react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import "./IntervalVisualizer.css";

function IntervalVisualizer({ intervals }) {
  if (!intervals || intervals.length === 0) {
    return (
      <div className="interval-visualizer empty">
        <p>No interval data available</p>
      </div>
    );
  }

  // Build power profile data points over time
  const buildPowerProfile = (intervals) => {
    const dataPoints = [];
    let cumulativeTime = 0;

    intervals.forEach((interval, index) => {
      const duration = interval.duration || 0;

      // Extract power values
      let startPower = 0;
      let endPower = 0;

      if (interval.powerTarget) {
        if (interval.powerTarget.type === "range") {
          // For range, start at min and ramp to max
          startPower = interval.powerTarget.min || 0;
          endPower = interval.powerTarget.max || startPower;
        } else if (interval.powerTarget.start && interval.powerTarget.end) {
          // For percentage-based ramps
          const ftp = 302; // Could be passed as prop
          startPower = Math.round(
            (interval.powerTarget.start.value || 0) * ftp,
          );
          endPower = Math.round((interval.powerTarget.end.value || 0) * ftp);
        } else if (typeof interval.powerTarget === "number") {
          startPower = interval.powerTarget;
          endPower = interval.powerTarget;
        }
      }

      // Add start point
      dataPoints.push({
        time: cumulativeTime / 60, // Convert to minutes
        power: startPower,
        interval: interval.name || `Interval ${index + 1}`,
        phase: "start",
      });

      // Add end point (creates the ramp)
      cumulativeTime += duration;
      dataPoints.push({
        time: cumulativeTime / 60,
        power: endPower,
        interval: interval.name || `Interval ${index + 1}`,
        phase: "end",
      });
    });

    return dataPoints;
  };

  const powerProfile = buildPowerProfile(intervals);

  // Calculate max power for Y-axis domain
  const maxPower = Math.max(...powerProfile.map((p) => p.power), 300);
  const yAxisMax = Math.ceil(maxPower / 50) * 50; // Round up to nearest 50

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload[0]) {
      const data = payload[0].payload;
      return (
        <div className="interval-tooltip">
          <h4>{data.interval}</h4>
          <p>
            <strong>Time:</strong> {Math.floor(data.time)}:
            {String(Math.round((data.time % 1) * 60)).padStart(2, "0")}
          </p>
          <p>
            <strong>Power:</strong> {Math.round(data.power)}W
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="interval-visualizer">
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart
          data={powerProfile}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="powerGradient" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor="var(--color-cycling)"
                stopOpacity={0.8}
              />
              <stop
                offset="95%"
                stopColor="var(--color-cycling)"
                stopOpacity={0.1}
              />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="time"
            label={{
              value: "Time (minutes)",
              position: "insideBottom",
              offset: -5,
            }}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            label={{
              value: "Power (watts)",
              angle: -90,
              position: "insideLeft",
            }}
            domain={[0, yAxisMax]}
            tick={{ fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={302}
            stroke="#2C5F2D"
            strokeDasharray="5 5"
            label="FTP"
          />
          <Area
            type="linear"
            dataKey="power"
            stroke="var(--color-cycling)"
            strokeWidth={3}
            fill="url(#powerGradient)"
            animationDuration={1000}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default IntervalVisualizer;
