"""
Interval Display Component

Streamlit component for visualizing detected workout intervals.
Shows interval breakdown, power/HR data, and workout structure.

Author: Fitness Tracker
Created: January 1, 2026
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Optional
import numpy as np


def format_time(seconds: int) -> str:
    """Format seconds to MM:SS or HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def get_interval_color(interval_type: str) -> str:
    """Get color for interval type"""
    colors = {
        'warmup': '#4CAF50',      # Green
        'work': '#FF5722',         # Red-orange
        'threshold': '#FF5722',    # Red-orange
        'threshold_long': '#D32F2F',  # Dark red
        'vo2max': '#9C27B0',      # Purple
        'sprint': '#F44336',       # Bright red
        'steady_state': '#2196F3', # Blue
        'recovery': '#81C784',     # Light green
        'rest': '#A5D6A7',        # Very light green
        'cooldown': '#66BB6A'     # Medium green
    }
    return colors.get(interval_type, '#757575')  # Default gray


def get_interval_emoji(interval_type: str) -> str:
    """Get emoji for interval type"""
    emojis = {
        'warmup': '🔥',
        'work': '💪',
        'threshold': '⚡',
        'threshold_long': '⚡⚡',
        'vo2max': '🚀',
        'sprint': '⚡',
        'steady_state': '🏃',
        'recovery': '😌',
        'rest': '💤',
        'cooldown': '❄️'
    }
    return emojis.get(interval_type, '📊')


def display_intervals_summary(intervals_data: Dict):
    """
    Display summary of detected intervals
    
    Args:
        intervals_data: Output from IntervalClassifier.classify_intervals()
    """
    if not intervals_data or not intervals_data.get('intervals'):
        st.info("No intervals detected for this workout")
        return
    
    # Show workout description
    description = intervals_data.get('description', 'Workout structure')
    st.markdown(f"**Workout Structure:** {description}")
    
    # Show summary stats
    summary = intervals_data.get('summary', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Intervals", summary.get('total_intervals', 0))
    
    with col2:
        st.metric("Work Intervals", summary.get('work_intervals', 0))
    
    with col3:
        st.metric("Rest Periods", summary.get('rest_intervals', 0))
    
    with col4:
        warmup = summary.get('warmup_count', 0)
        cooldown = summary.get('cooldown_count', 0)
        st.metric("Warmup/Cooldown", f"{warmup}/{cooldown}")


def display_intervals_table(intervals_data: Dict):
    """
    Display detailed table of intervals
    
    Args:
        intervals_data: Output from IntervalClassifier.classify_intervals()
    """
    if not intervals_data or not intervals_data.get('intervals'):
        return
    
    intervals = intervals_data['intervals']
    
    # Convert to DataFrame
    df_data = []
    for interval in intervals:
        emoji = get_interval_emoji(interval['type'])
        
        df_data.append({
            '': emoji,
            'Type': interval['type'].replace('_', ' ').title(),
            'Start': format_time(interval['start_time']),
            'Duration': format_time(interval['duration_sec']),
            'Zone': interval['intensity_zone'],
            'Avg Power': f"{int(interval['avg_power'])}W",
            'NP': f"{int(interval['normalized_power'])}W",
            'Max Power': f"{int(interval['max_power'])}W",
            '% FTP': f"{interval['percent_ftp']:.0f}%",
            'Avg HR': f"{int(interval['avg_hr'])}bpm" if interval.get('avg_hr') else '-',
            'Avg Cadence': f"{int(interval['avg_cadence'])}" if interval.get('avg_cadence') else '-'
        })
    
    df = pd.DataFrame(df_data)
    
    # Style the dataframe
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


def plot_intervals_on_power_curve(intervals_data: Dict, power_series: List[float], 
                                   hr_series: Optional[List[float]] = None):
    """
    Plot power curve with interval highlighting
    
    Args:
        intervals_data: Output from IntervalClassifier.classify_intervals()
        power_series: Full workout power data (one per second)
        hr_series: Optional HR data
    """
    if not intervals_data or not intervals_data.get('intervals'):
        return
    
    intervals = intervals_data['intervals']
    
    # Create figure with secondary y-axis for HR
    fig = go.Figure()
    
    # Time axis (seconds)
    time_seconds = list(range(len(power_series)))
    time_formatted = [format_time(t) for t in time_seconds]
    
    # Add power curve
    fig.add_trace(go.Scatter(
        x=time_seconds,
        y=power_series,
        mode='lines',
        name='Power',
        line=dict(color='#2196F3', width=1),
        hovertemplate='Time: %{text}<br>Power: %{y}W<extra></extra>',
        text=time_formatted
    ))
    
    # Add HR curve if available
    if hr_series and len(hr_series) == len(power_series):
        fig.add_trace(go.Scatter(
            x=time_seconds,
            y=hr_series,
            mode='lines',
            name='Heart Rate',
            line=dict(color='#E91E63', width=1),
            yaxis='y2',
            hovertemplate='Time: %{text}<br>HR: %{y}bpm<extra></extra>',
            text=time_formatted
        ))
    
    # Add interval highlighting
    for interval in intervals:
        color = get_interval_color(interval['type'])
        
        # Add shaded region for interval
        fig.add_vrect(
            x0=interval['start_time'],
            x1=interval['end_time'],
            fillcolor=color,
            opacity=0.2,
            line_width=0,
            annotation_text=interval['type'].replace('_', ' ').title(),
            annotation_position="top",
            annotation=dict(
                font_size=10,
                font_color=color
            )
        )
    
    # Update layout
    fig.update_layout(
        title="Power & Heart Rate with Detected Intervals",
        xaxis_title="Time",
        yaxis_title="Power (W)",
        yaxis2=dict(
            title="Heart Rate (bpm)",
            overlaying='y',
            side='right'
        ),
        hovermode='x unified',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Format x-axis ticks (show every 5 minutes)
    tick_interval = 5 * 60  # 5 minutes
    tick_vals = list(range(0, len(power_series), tick_interval))
    tick_text = [format_time(t) for t in tick_vals]
    
    fig.update_xaxes(
        tickmode='array',
        tickvals=tick_vals,
        ticktext=tick_text
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_intervals_analysis(intervals_data: Dict, power_series: Optional[List[float]] = None,
                               hr_series: Optional[List[float]] = None):
    """
    Complete interval analysis display (summary, table, and chart)
    
    Args:
        intervals_data: Output from IntervalClassifier.classify_intervals()
        power_series: Optional full workout power data for visualization
        hr_series: Optional full workout HR data
    """
    if not intervals_data or not intervals_data.get('intervals'):
        return
    
    st.markdown("### 📊 Detected Intervals")
    
    # Summary metrics
    display_intervals_summary(intervals_data)
    
    st.markdown("---")
    
    # Power curve with intervals
    if power_series:
        plot_intervals_on_power_curve(intervals_data, power_series, hr_series)
        st.markdown("---")
    
    # Detailed table
    with st.expander("📋 Detailed Interval Breakdown", expanded=False):
        display_intervals_table(intervals_data)
        
        # Show detection metadata
        st.caption(f"**Detection Algorithm:** v{intervals_data.get('algorithm_version', 'unknown')} | "
                  f"**Detected:** {intervals_data.get('detected_at', 'unknown')}")


def display_interval_comparison(current_intervals: Dict, historical_intervals: List[Dict]):
    """
    Compare current workout intervals to similar historical workouts
    
    Args:
        current_intervals: Intervals from current workout
        historical_intervals: List of intervals from historical workouts
    """
    st.markdown("### 📈 Interval Comparison")
    
    # TODO: Implement when we have session comparison feature
    st.info("Interval comparison coming soon! This will show how your intervals compare to similar past workouts.")
