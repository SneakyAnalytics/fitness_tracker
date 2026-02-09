import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import './IntervalVisualizer.css';

function IntervalVisualizer({ intervals }) {
  if (!intervals || intervals.length === 0) {
    return (
      <div className="interval-visualizer empty">
        <p>No interval data available</p>
      </div>
    );
  }

  // Process intervals for display
  const processedIntervals = intervals.map((interval, index) => ({
    name: interval.name || `Interval ${index + 1}`,
    duration: interval.duration || 0,
    intensity: interval.intensity || 'moderate',
    power: interval.power_avg || interval.power || 0,
    hr: interval.hr_avg || interval.hr || 0,
    ...interval
  }));

  // Color mapping for intensity zones
  const getBarColor = (intensity) => {
    const colorMap = {
      'recovery': '#7DB3D5',
      'easy': '#56C596',
      'moderate': '#B8956A',
      'hard': '#FF8C42',
      'max': '#EF5350',
      'z1': '#7DB3D5',
      'z2': '#56C596',
      'z3': '#B8956A',
      'z4': '#FF8C42',
      'z5': '#EF5350',
    };
    return colorMap[intensity?.toLowerCase()] || '#B8956A';
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload[0]) {
      const data = payload[0].payload;
      return (
        <div className="interval-tooltip">
          <h4>{data.name}</h4>
          <p><strong>Duration:</strong> {formatDuration(data.duration)}</p>
          {data.power > 0 && <p><strong>Power:</strong> {data.power}W</p>}
          {data.hr > 0 && <p><strong>HR:</strong> {data.hr} bpm</p>}
          {data.intensity && <p><strong>Intensity:</strong> {data.intensity}</p>}
        </div>
      );
    }
    return null;
  };

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`;
  };

  return (
    <div className="interval-visualizer">
      <div className="visualizer-header">
        <h3>Workout Structure</h3>
        <div className="intensity-legend">
          <span className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: '#7DB3D5' }}></span>
            Recovery
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: '#56C596' }}></span>
            Easy
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: '#B8956A' }}></span>
            Moderate
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: '#FF8C42' }}></span>
            Hard
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ backgroundColor: '#EF5350' }}></span>
            Max
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={processedIntervals} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8E8DD" />
          <XAxis 
            dataKey="name" 
            angle={-45}
            textAnchor="end"
            height={80}
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            label={{ value: 'Duration (min)', angle: -90, position: 'insideLeft' }}
            tickFormatter={(value) => Math.round(value / 60)}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="duration" radius={[8, 8, 0, 0]}>
            {processedIntervals.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBarColor(entry.intensity)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="interval-summary">
        <div className="summary-stat">
          <span className="stat-label">Total Time</span>
          <span className="stat-value">
            {formatDuration(processedIntervals.reduce((sum, i) => sum + i.duration, 0))}
          </span>
        </div>
        <div className="summary-stat">
          <span className="stat-label">Intervals</span>
          <span className="stat-value">{processedIntervals.length}</span>
        </div>
      </div>
    </div>
  );
}

export default IntervalVisualizer;
