"""
Session Comparison UI Component

Displays side-by-side comparison of similar workouts
"""

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional
import json
import pandas as pd


def display_session_comparison(workout1: Dict[str, Any], workout2: Dict[str, Any], 
                               comparison: Dict[str, Any]):
    """
    Display comprehensive comparison between two workouts
    
    Args:
        workout1: First workout dict
        workout2: Second workout dict  
        comparison: Comparison results from WorkoutComparator
    """
    
    # Header
    st.markdown("### 📊 Session Comparison")
    
    # Workout headers
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Workout 1: {comparison['workout1']['date']}**")
        st.caption(comparison['workout1']['title'])
    
    with col2:
        st.markdown(f"**Workout 2: {comparison['workout2']['date']}**")
        st.caption(comparison['workout2']['title'])
    
    # Metrics comparison
    st.markdown("---")
    st.markdown("#### Key Metrics")
    
    metrics_data = []
    for metric_name, metric_data in comparison.get('metrics', {}).items():
        
        # Format metric name
        display_name = metric_name.upper() if len(metric_name) <= 3 else metric_name.title()
        
        # Format values
        val1 = metric_data['workout1']
        val2 = metric_data['workout2']
        change = metric_data['change']
        change_pct = metric_data['change_pct']
        
        # Determine if improvement
        is_improvement = change > 0  # For most metrics, higher is better
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        color = "🟢" if is_improvement and abs(change_pct) > 2 else "🔴" if not is_improvement and abs(change_pct) > 2 else "⚪"
        
        metrics_data.append({
            'Metric': display_name,
            'Workout 1': f"{val1:.1f}",
            'Workout 2': f"{val2:.1f}",
            'Change': f"{arrow} {abs(change):.1f} ({abs(change_pct):.1f}%)",
            'Status': color
        })
    
    if metrics_data:
        df = pd.DataFrame(metrics_data)
        st.dataframe(df, hide_index=True, use_container_width=True)
    
    # Interval comparison
    if comparison.get('intervals'):
        st.markdown("---")
        st.markdown("#### Interval Execution")
        
        interval_data = comparison['intervals']
        
        # Work interval count
        count1 = interval_data['work_interval_count']['workout1']
        count2 = interval_data['work_interval_count']['workout2']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Work Intervals", f"{count1} vs {count2}")
        
        # Average power comparison
        if 'avg_work_power' in interval_data:
            power_data = interval_data['avg_work_power']
            with col2:
                st.metric(
                    "Avg Work Power",
                    f"{power_data['workout1']:.0f}W",
                    delta=f"{power_data['change']:+.0f}W ({power_data['change_pct']:+.1f}%)",
                    delta_color="normal"
                )
        
        # Average HR comparison
        if 'avg_work_hr' in interval_data:
            hr_data = interval_data['avg_work_hr']
            with col3:
                st.metric(
                    "Avg Work HR",
                    f"{hr_data['workout1']:.0f} bpm",
                    delta=f"{hr_data['change']:+.0f} bpm ({hr_data['change_pct']:+.1f}%)",
                    delta_color="inverse"  # Lower HR is better
                )
    
    # Improvements summary
    if comparison.get('improvements'):
        st.markdown("---")
        st.markdown("#### 💡 Key Observations")
        
        for improvement in comparison['improvements']:
            st.markdown(f"• {improvement}")
    
    # Power curve overlay (if we have power data)
    st.markdown("---")
    st.markdown("#### Power & Heart Rate Comparison")
    
    # Check if we have power and HR series data - try both workout_data and analysis_data
    power_series1 = None
    power_series2 = None
    hr_series1 = None
    hr_series2 = None
    
    # Try getting from analysis_data first (new format)
    if workout1.get('analysis_data'):
        try:
            analysis_data1 = workout1['analysis_data']
            if isinstance(analysis_data1, str):
                analysis_data1 = json.loads(analysis_data1)
            
            parsed_data1 = analysis_data1.get('parsed_data', {})
            power_metrics1 = parsed_data1.get('power_metrics', {})
            power_series1 = power_metrics1.get('power_series')
            
            # Get HR series
            hr_metrics1 = parsed_data1.get('hr_metrics', {})
            hr_series1 = hr_metrics1.get('hr_series')
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    
    # Fallback to workout_data (old format)
    if not power_series1 and workout1.get('workout_data'):
        try:
            data1 = json.loads(workout1.get('workout_data', '{}'))
            power_data1 = data1.get('power_data', {})
            power_series1 = power_data1.get('power_series')
            hr_data1 = data1.get('hr_data', {})
            hr_series1 = hr_data1.get('hr_series')
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    
    # Try getting from analysis_data first (new format)
    if workout2.get('analysis_data'):
        try:
            analysis_data2 = workout2['analysis_data']
            if isinstance(analysis_data2, str):
                analysis_data2 = json.loads(analysis_data2)
            
            parsed_data2 = analysis_data2.get('parsed_data', {})
            power_metrics2 = parsed_data2.get('power_metrics', {})
            power_series2 = power_metrics2.get('power_series')
            
            # Get HR series
            hr_metrics2 = parsed_data2.get('hr_metrics', {})
            hr_series2 = hr_metrics2.get('hr_series')
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    
    # Fallback to workout_data (old format)
    if not power_series2 and workout2.get('workout_data'):
        try:
            data2 = json.loads(workout2.get('workout_data', '{}'))
            power_data2 = data2.get('power_data', {})
            power_series2 = power_data2.get('power_series')
            hr_data2 = data2.get('hr_data', {})
            hr_series2 = hr_data2.get('hr_series')
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    
    if power_series1 and power_series2:
        display_power_hr_overlay(
            power_series1, power_series2,
            hr_series1, hr_series2,
            comparison['workout1']['date'],
            comparison['workout2']['date']
        )
    else:
        st.info("Power curve overlay requires FIT file data for both workouts")


def display_power_hr_overlay(
    power_series1: List[float], power_series2: List[float],
    hr_series1: Optional[List[float]], hr_series2: Optional[List[float]],
    date1: str, date2: str
):
    """
    Display overlaid power and heart rate curves for two workouts
    
    Args:
        power_series1: Power series data for first workout (list of watts)
        power_series2: Power series data for second workout (list of watts)
        hr_series1: Heart rate series for first workout (optional)
        hr_series2: Heart rate series for second workout (optional)
        date1: Date of first workout
        date2: Date of second workout
    """
    
    fig = go.Figure()
    
    # Power series is already a list of values
    if not power_series1 or not power_series2:
        st.warning("Power series data not available for comparison")
        return
    
    # Create time arrays (in minutes)
    time1 = [i for i in range(len(power_series1))]  # Keep in seconds for better resolution
    time2 = [i for i in range(len(power_series2))]
    
    # Add power traces (bold and prominent)
    fig.add_trace(go.Scatter(
        x=time1,
        y=power_series1,
        mode='lines',
        name=f'🔵 Power {date1}',
        line=dict(color='#0066CC', width=3.5),  # Deep blue, very thick
        opacity=1.0,
        yaxis='y1',
        legendgroup='workout1',
        hovertemplate='<b>Power:</b> %{y:.0f}W<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=time2,
        y=power_series2,
        mode='lines',
        name=f'🟠 Power {date2}',
        line=dict(color='#FF6B35', width=3, dash='dot'),  # Bright coral, thick dotted
        opacity=0.95,
        yaxis='y1',
        legendgroup='workout2',
        hovertemplate='<b>Power:</b> %{y:.0f}W<extra></extra>'
    ))
    
    # Add heart rate traces if available (thinner, more subtle)
    has_hr = False
    if hr_series1 and len(hr_series1) > 0:
        has_hr = True
        # Ensure HR series matches power series length
        hr_time1 = time1[:len(hr_series1)] if len(hr_series1) < len(time1) else time1
        hr_data1 = hr_series1[:len(hr_time1)]
        
        fig.add_trace(go.Scatter(
            x=hr_time1,
            y=hr_data1,
            mode='lines',
            name=f'❤️  HR {date1}',
            line=dict(color='#DC143C', width=2),  # Crimson red, thinner
            opacity=0.6,
            yaxis='y2',
            legendgroup='workout1',
            hovertemplate='<b>HR:</b> %{y:.0f} bpm<extra></extra>'
        ))
    
    if hr_series2 and len(hr_series2) > 0:
        has_hr = True
        # Ensure HR series matches power series length
        hr_time2 = time2[:len(hr_series2)] if len(hr_series2) < len(time2) else time2
        hr_data2 = hr_series2[:len(hr_time2)]
        
        fig.add_trace(go.Scatter(
            x=hr_time2,
            y=hr_data2,
            mode='lines',
            name=f'🧡 HR {date2}',
            line=dict(color='#FF8C42', width=1.8, dash='dot'),  # Orange, thin dotted
            opacity=0.55,
            yaxis='y2',
            legendgroup='workout2',
            hovertemplate='<b>HR:</b> %{y:.0f} bpm<extra></extra>'
        ))
    
    # Configure layout with dual y-axes
    layout_config = {
        'title': {
            'text': 'Power & Heart Rate Comparison',
            'font': {'size': 20, 'color': '#2C3E50'}
        },
        'xaxis': {
            'title': {'text': 'Time (seconds)', 'font': {'size': 14}},
            'showgrid': True,
            'gridcolor': '#E8E8E8',
            'gridwidth': 1
        },
        'yaxis': {
            'title': {'text': 'Power (watts)', 'font': {'size': 14, 'color': '#0066CC'}},
            'side': 'left',
            'showgrid': True,
            'gridcolor': '#E8E8E8',
            'gridwidth': 1
        },
        'hovermode': 'x unified',
        'hoverlabel': {
            'bgcolor': '#1a1a1a',  # Very dark background
            'font': {
                'size': 15,
                'color': 'white',
                'family': 'Arial, sans-serif'
            },
            'namelength': -1,
            'bordercolor': 'white',
            'align': 'left'
        },
        'height': 550,
        'showlegend': True,
        'legend': {
            'orientation': 'v',  # Vertical legend for clarity
            'yanchor': 'top',
            'y': 0.99,
            'xanchor': 'left',
            'x': 0.01,
            'bgcolor': 'rgba(255,255,255,0.95)',
            'bordercolor': '#999',
            'borderwidth': 2,
            'font': {'size': 13, 'color': '#2C3E50'}
        },
        'plot_bgcolor': 'white',
        'paper_bgcolor': '#F8F9FA'
    }
    
    # Add secondary y-axis for heart rate if we have HR data
    if has_hr:
        layout_config['yaxis2'] = {
            'title': {'text': 'Heart Rate (bpm)', 'font': {'size': 14, 'color': '#DC143C'}},
            'side': 'right',
            'overlaying': 'y',
            'showgrid': False,
            'range': [60, 200]  # Typical HR range for better scaling
        }
    
    fig.update_layout(**layout_config)
    
    st.plotly_chart(fig, use_container_width=True)


def display_similar_workouts_list(similar_workouts: List[tuple], target_date: str):
    """
    Display a list of similar workouts with similarity scores
    
    Args:
        similar_workouts: List of (workout, similarity_score) tuples
        target_date: Date of the target workout for reference
    """
    
    if not similar_workouts:
        st.info(f"No similar workouts found. Try adjusting the similarity threshold.")
        return
    
    st.markdown(f"### 🔍 Workouts Similar to {target_date}")
    st.caption(f"Found {len(similar_workouts)} similar session(s)")
    
    for idx, (workout, similarity) in enumerate(similar_workouts, 1):
        with st.expander(f"#{idx} - {workout['workout_day']} (Similarity: {similarity:.0f}%)"):
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{workout['workout_title']}**")
                
                # Parse workout data
                data = json.loads(workout.get('workout_data', '{}'))
                analysis = json.loads(workout.get('analysis_data', '{}'))
                
                # Display key metrics
                metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                
                with metrics_col1:
                    tss = data.get('tss', 'N/A')
                    st.metric("TSS", tss)
                
                with metrics_col2:
                    duration = data.get('duration', 'N/A')
                    st.metric("Duration", f"{duration} min" if duration != 'N/A' else 'N/A')
                
                with metrics_col3:
                    intervals = analysis.get('intervals', {})
                    interval_count = len(intervals.get('intervals', [])) if intervals else 0
                    st.metric("Intervals", interval_count)
            
            with col2:
                # Similarity indicator
                st.markdown(f"**Match Score**")
                st.progress(similarity / 100)
                st.caption(f"{similarity:.0f}%")
            
            # Compare button
            if st.button(f"Compare with {workout['workout_day']}", key=f"compare_{workout['id']}"):
                st.session_state['comparison_workout_id'] = workout['id']
                st.rerun()


def display_find_similar_ui(workouts_df: pd.DataFrame):
    """
    Display UI for finding similar workouts
    
    Args:
        workouts_df: DataFrame with available workouts
    """
    
    st.markdown("### 🔎 Find Similar Workouts")
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        # Select target workout
        workout_options = workouts_df['workout_day'] + ' - ' + workouts_df['workout_title'].str[:50]
        selected_workout = st.selectbox(
            "Select workout to find matches for:",
            options=range(len(workout_options)),
            format_func=lambda x: workout_options.iloc[x]
        )
    
    with col2:
        # Similarity threshold
        min_similarity = st.slider(
            "Minimum similarity score:",
            min_value=30,
            max_value=90,
            value=50,
            step=5,
            help="Higher values find more similar workouts (stricter matching)"
        )
    
    # Number of results
    max_results = st.number_input(
        "Maximum results to show:",
        min_value=1,
        max_value=20,
        value=5
    )
    
    return selected_workout, min_similarity, max_results
