"""
Interactive Plotly visualizations for workout analysis
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, Any, List, Optional


class WorkoutVisualizer:
    """Create interactive Plotly graphs for workout data"""
    
    def __init__(self):
        # Default color scheme
        self.colors = {
            'power': '#FF6B6B',
            'hr': '#EE5A6F',
            'cadence': '#4ECDC4',
            'speed': '#95E1D3',
            'elevation': '#C7CEEA',
            'zones': {
                'Zone 1': '#38A169',
                'Zone 2': '#48BB78',
                'Zone 3': '#ECC94B',
                'Zone 4': '#ED8936',
                'Zone 5': '#E53E3E'
            }
        }
    
    def create_workout_dashboard(self, parsed_data: Dict[str, Any], 
                                 peak_efforts: Optional[Dict[str, Dict[str, float]]] = None) -> go.Figure:
        """
        Create a comprehensive multi-panel workout dashboard
        
        Args:
            parsed_data: Parsed FIT file data from FitParser
            peak_efforts: Optional peak efforts from FitFileAnalyzer
            
        Returns:
            Plotly Figure object
        """
        power_metrics = parsed_data.get('power_metrics', {})
        hr_metrics = parsed_data.get('hr_metrics', {})
        time_series = parsed_data.get('time_series', {})
        
        # Determine what data we have from time_series
        has_power = time_series and time_series.get('power') and len(time_series['power']) > 0
        has_hr = time_series and time_series.get('hr') and len([x for x in time_series['hr'] if x]) > 0
        has_cadence = time_series and time_series.get('cadence') and len([x for x in time_series['cadence'] if x]) > 0
        
        if not has_power and not has_hr:
            # No data to display
            fig = go.Figure()
            fig.add_annotation(
                text="No power or heart rate data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20)
            )
            return fig
        
        # Create subplot titles based on available data
        subplot_titles = []
        if has_power:
            subplot_titles.append('Power Output')
        if has_hr:
            subplot_titles.append('Heart Rate')
        if has_cadence:
            subplot_titles.append('Cadence')
        
        num_plots = len(subplot_titles)
        
        # Create subplots for time series only
        fig = make_subplots(
            rows=num_plots,
            cols=1,
            subplot_titles=subplot_titles,
            vertical_spacing=0.08,
            specs=[[{'type': 'xy'}] for _ in range(num_plots)]  # Explicitly XY plots
        )
        
        row_idx = 1
        
        # Add power data
        if has_power:
            power_series = np.array(time_series['power'])
            time_minutes = np.arange(len(power_series)) / 60  # Convert seconds to minutes
            
            # Main power trace
            fig.add_trace(
                go.Scatter(
                    x=time_minutes,
                    y=power_series,
                    mode='lines',
                    name='Power',
                    line=dict(color=self.colors['power'], width=2),
                    fill='tozeroy',
                    fillcolor='rgba(255, 107, 107, 0.3)',
                    hovertemplate='<b>Time:</b> %{x:.1f} min<br><b>Power:</b> %{y:.0f}W<extra></extra>'
                ),
                row=row_idx, col=1
            )
            
            # Add average power line
            if power_metrics and 'average_power' in power_metrics:
                avg_power = power_metrics.get('average_power', 0)
                fig.add_hline(
                    y=avg_power,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=f"Avg: {avg_power:.0f}W",
                    row=row_idx, col=1
                )
            
            # Add normalized power line
            np_power = power_metrics.get('normalized_power', 0)
            if np_power > 0:
                fig.add_hline(
                    y=np_power,
                    line_dash="dot",
                    line_color="blue",
                    annotation_text=f"NP: {np_power:.0f}W",
                    row=row_idx, col=1
                )
            
            # Highlight peak efforts if provided
            if peak_efforts:
                for effort_name, effort_data in peak_efforts.items():
                    start_idx = effort_data.get('index', 0)
                    duration = effort_data.get('duration_seconds', 0)
                    end_idx = start_idx + duration
                    
                    if end_idx < len(power_series):
                        fig.add_vrect(
                            x0=start_idx / 60,
                            x1=end_idx / 60,
                            fillcolor="yellow",
                            opacity=0.2,
                            layer="below",
                            line_width=0,
                            annotation_text=effort_name,
                            annotation_position="top left",
                            row=row_idx, col=1
                        )
            
            fig.update_xaxes(title_text="Time (minutes)", row=row_idx, col=1)
            fig.update_yaxes(title_text="Power (watts)", row=row_idx, col=1)
            row_idx += 1
        
        # Add heart rate data
        if has_hr:
            hr_series = np.array([x if x else np.nan for x in time_series['hr']])
            time_minutes = np.arange(len(hr_series)) / 60
            
            fig.add_trace(
                go.Scatter(
                    x=time_minutes,
                    y=hr_series,
                    mode='lines',
                    name='Heart Rate',
                    line=dict(color=self.colors['hr'], width=2),
                    fill='tozeroy',
                    fillcolor='rgba(238, 90, 111, 0.3)',
                    hovertemplate='<b>Time:</b> %{x:.1f} min<br><b>HR:</b> %{y:.0f} bpm<extra></extra>'
                ),
                row=row_idx, col=1
            )
            
            # Add average HR line
            if hr_metrics and 'average_hr' in hr_metrics:
                avg_hr = hr_metrics['average_hr']
                fig.add_hline(
                    y=avg_hr,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=f"Avg: {avg_hr:.0f} bpm",
                    row=row_idx, col=1
                )
            
            fig.update_xaxes(title_text="Time (minutes)", row=row_idx, col=1)
            fig.update_yaxes(title_text="Heart Rate (bpm)", row=row_idx, col=1)
            row_idx += 1
        
        # Add cadence data
        if has_cadence:
            cadence_series = np.array([x if x else np.nan for x in time_series['cadence']])
            time_minutes = np.arange(len(cadence_series)) / 60
            
            fig.add_trace(
                go.Scatter(
                    x=time_minutes,
                    y=cadence_series,
                    mode='lines',
                    name='Cadence',
                    line=dict(color=self.colors['cadence'], width=2),
                    fill='tozeroy',
                    fillcolor='rgba(78, 205, 196, 0.3)',
                    hovertemplate='<b>Time:</b> %{x:.1f} min<br><b>Cadence:</b> %{y:.0f} rpm<extra></extra>'
                ),
                row=row_idx, col=1
            )
            
            # Add average cadence line if available
            avg_cadence = np.nanmean(cadence_series)
            if not np.isnan(avg_cadence):
                fig.add_hline(
                    y=avg_cadence,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=f"Avg: {avg_cadence:.0f} rpm",
                    row=row_idx, col=1
                )
            
            fig.update_xaxes(title_text="Time (minutes)", row=row_idx, col=1)
            fig.update_yaxes(title_text="Cadence (rpm)", row=row_idx, col=1)
            row_idx += 1
        
        # Update layout
        fig.update_layout(
            height=350 * num_plots,  # Smaller height per plot
            showlegend=False,
            title_text="Workout Time Series",
            title_x=0.5,
            hovermode='x unified',
            template='plotly_dark'
        )
        
        return fig
    
    def create_peak_power_curve(self, peak_efforts: Dict[str, Dict[str, float]], 
                               historical_bests: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> go.Figure:
        """
        Create a peak power curve graph
        
        Args:
            peak_efforts: Current workout peak efforts
            historical_bests: Optional historical personal bests
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        # Extract durations and powers
        durations = []
        powers = []
        labels = []
        
        duration_mapping = {
            '30s': 30,
            '1min': 60,
            '3min': 180,
            '5min': 300,
            '10min': 600,
            '20min': 1200,
            '45min': 2700,
            '60min': 3600
        }
        
        for effort_name, effort_data in sorted(peak_efforts.items(), 
                                               key=lambda x: duration_mapping.get(x[0], 0)):
            duration = duration_mapping.get(effort_name, 0)
            if duration > 0:
                durations.append(duration)
                powers.append(effort_data['power'])
                labels.append(effort_name)
        
        # Current workout curve
        fig.add_trace(go.Scatter(
            x=durations,
            y=powers,
            mode='lines+markers',
            name='Current Workout',
            line=dict(color=self.colors['power'], width=3),
            marker=dict(size=10),
            hovertemplate='<b>%{text}</b><br>%{y:.0f}W<extra></extra>',
            text=labels
        ))
        
        # Add historical bests if provided
        if historical_bests:
            hist_durations = []
            hist_powers = []
            hist_labels = []
            
            for effort_type, bests in historical_bests.items():
                if bests and effort_type in duration_mapping:
                    # Use the gold medal (rank 1) value
                    gold = next((b for b in bests if b.get('rank') == 1), None)
                    if gold:
                        hist_durations.append(duration_mapping[effort_type])
                        hist_powers.append(gold['effort_value'])
                        hist_labels.append(effort_type)
            
            if hist_durations:
                fig.add_trace(go.Scatter(
                    x=hist_durations,
                    y=hist_powers,
                    mode='lines+markers',
                    name='All-Time Bests',
                    line=dict(color='gold', width=3, dash='dash'),
                    marker=dict(size=10, symbol='star'),
                    hovertemplate='<b>%{text}</b><br>%{y:.0f}W (PB)<extra></extra>',
                    text=hist_labels
                ))
        
        fig.update_layout(
            title="Peak Power Curve",
            xaxis_title="Duration (seconds)",
            yaxis_title="Power (watts)",
            xaxis_type="log",
            height=500,
            hovermode='closest',
            showlegend=True
        )
        
        return fig
    
    def create_zone_comparison(self, actual_zones: Dict[str, float], 
                              planned_zones: Optional[Dict[str, float]] = None) -> go.Figure:
        """
        Create bar chart comparing actual vs planned zone distribution
        
        Args:
            actual_zones: Actual time in zones from completed workout
            planned_zones: Optional planned zone distribution
            
        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        
        zone_names = list(actual_zones.keys())
        actual_values = list(actual_zones.values())
        
        fig.add_trace(go.Bar(
            name='Actual',
            x=zone_names,
            y=actual_values,
            marker_color=self.colors['power']
        ))
        
        if planned_zones:
            planned_values = [planned_zones.get(z, 0) for z in zone_names]
            fig.add_trace(go.Bar(
                name='Planned',
                x=zone_names,
                y=planned_values,
                marker_color=self.colors['cadence'],
                opacity=0.6
            ))
        
        fig.update_layout(
            title="Zone Distribution: Actual vs Planned",
            xaxis_title="Power Zone",
            yaxis_title="Time (%)",
            barmode='group',
            height=400,
            showlegend=True
        )
        
        return fig
