# src/ui/streamlit_app.py
import sys
sys.path.append(".")

import os
import streamlit as st
import pandas as pd

# Some versions of NumPy (e.g. 1.26+) do not expose a top-level `numpy.rec` module
# which older code (and pandas internals) sometimes expect to import. Ensure a
# compatible alias exists so downstream `isinstance(..., np.rec.recarray)` checks
# don't raise ModuleNotFoundError at runtime.
try:
    import numpy as np
    import importlib
    try:
        # Try importing the historical alias first (may raise ModuleNotFoundError)
        import numpy.rec  # type: ignore
    except Exception:
        try:
            rec_mod = importlib.import_module('numpy.core.records')
            setattr(np, 'rec', rec_mod)
        except Exception:
            # If this fails, we silently continue; the original import error
            # will surface later but we've attempted a safe compatibility fix.
            pass
except Exception:
    # If numpy isn't available at all, let the normal import errors occur later
    pass
from datetime import datetime, timedelta, date
from typing import Any, Optional, cast
import requests

# API URL configuration - supports both Docker and native environments
API_URL = os.getenv("API_URL", "http://localhost:8000")
import json
import importlib
import types as _types

# Try to import python-dotenv for environment variable loading
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = lambda: None  # No-op function if dotenv not available

# Some versions of plotly may expect a submodule `plotly.graph_objs._densitymap`
# to exist (older code paths). If that submodule is missing in the installed
# plotly package, create a compatibility alias pointing at a closely related
# existing module (if available) or a dummy module to avoid import-time
# failures inside plotly's lazy importer.
try:
    import plotly.graph_objs as _go  # type: ignore
    try:
        # Quick existence check
        import plotly.graph_objs._densitymap  # type: ignore
    except Exception:
        # Try to reuse a related module if present
        for _candidate in ('plotly.graph_objs._densitymapbox', 'plotly.graph_objs._scatter', 'plotly.graph_objs._box'):
            try:
                _mod = importlib.import_module(_candidate)
                sys.modules['plotly.graph_objs._densitymap'] = _mod
                break
            except Exception:
                continue
        else:
            # Last resort: insert an empty module object so importlib can find it
            sys.modules['plotly.graph_objs._densitymap'] = _types.ModuleType('plotly.graph_objs._densitymap')
except Exception:
    # If plotly isn't installed or another error occurs, let the normal import
    # errors surface when plotly is actually needed.
    pass

import plotly.express as px
import os
import math

def apply_custom_styling():
    """Apply custom CSS styling to enhance the app's appearance"""
    st.markdown("""
    <style>
    /* Main app styling */
    .main-header {
        background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        color: white !important;
        font-size: 2.5rem !important;
        margin: 0 !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8fdf4;
    }
    
    /* Metric cards styling */
    [data-testid="metric-container"] {
        background: linear-gradient(45deg, #a8e063 0%, #56ab2f 100%);
        border: none;
        padding: 1rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
    
    [data-testid="metric-container"] > div {
        color: white !important;
    }
    
    [data-testid="metric-container"] label {
        color: white !important;
        font-weight: 600;
    }
    
    /* Custom metric card variants */
    .metric-card-blue {
        background: linear-gradient(45deg, #56ab2f 0%, #7fb800 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
    
    .metric-card-green {
        background: linear-gradient(45deg, #a8e063 0%, #d4fc79 100%);
        padding: 1rem;
        border-radius: 10px;
        color: #2d5016;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        font-weight: 600;
    }
    
    .metric-card-orange {
        background: linear-gradient(45deg, #f9ca24 0%, #f0932b 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
    
    .metric-card-purple {
        background: linear-gradient(45deg, #badc58 0%, #6c5ce7 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #56ab2f 0%, #a8e063 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        background: linear-gradient(45deg, #4a9a26 0%, #9fd157 100%);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(45deg, #f9ca24 0%, #a8e063 100%);
        border-radius: 8px;
        padding: 0.5rem;
        margin-bottom: 0.5rem;
        color: #2d5016;
        font-weight: 600;
    }
    
    /* Table styling */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Success/Info messages */
    .stSuccess {
        background: linear-gradient(45deg, #56ab2f 0%, #a8e063 100%);
        border-radius: 8px;
    }
    
    .stInfo {
        background: linear-gradient(45deg, #7fb800 0%, #badc58 100%);
        border-radius: 8px;
    }
    
    .stError {
        background: linear-gradient(45deg, #eb4d4b 0%, #f0932b 100%);
        border-radius: 8px;
    }
    
    /* Custom section headers */
    .section-header {
        background: linear-gradient(45deg, #56ab2f 0%, #a8e063 100%);
        color: white;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 1rem 0 0.5rem 0;
        text-align: center;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Workout type badges */
    .workout-badge-cycling {
        background: linear-gradient(45deg, #f9ca24 0%, #f0932b 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.2rem;
        display: inline-block;
    }
    
    .workout-badge-running {
        background: linear-gradient(45deg, #56ab2f 0%, #7fb800 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.2rem;
        display: inline-block;
    }
    
    .workout-badge-strength {
        background: linear-gradient(45deg, #badc58 0%, #6c5ce7 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.2rem;
        display: inline-block;
    }
    
    /* Calendar styling */
    .calendar-day {
        border: 2px solid #e1e1e1;
        border-radius: 8px;
        padding: 0.5rem;
        margin: 0.2rem;
        transition: all 0.3s ease;
    }
    
    .calendar-day:hover {
        border-color: #56ab2f;
        transform: scale(1.02);
    }
    
    .calendar-day-has-workout {
        background: linear-gradient(45deg, #a8e063 0%, #d4fc79 100%);
        border-color: #56ab2f;
    }
    </style>
    """, unsafe_allow_html=True)

def create_custom_metric(title, value, icon="📊", color="blue"):
    """Create a custom styled metric card"""
    color_class = f"metric-card-{color}"
    st.markdown(f"""
    <div class="{color_class}">
        <h3>{icon} {title}</h3>
        <h2>{value}</h2>
    </div>
    """, unsafe_allow_html=True)

def create_section_header(text, icon="🏃‍♂️"):
    """Create a styled section header"""
    st.markdown(f"""
    <div class="section-header">
        {icon} {text}
    </div>
    """, unsafe_allow_html=True)

def create_workout_badge(workout_type):
    """Create a styled workout type badge"""
    badges = {
        "cycling": ("🚴‍♂️", "workout-badge-cycling"),
        "bike": ("🚴‍♂️", "workout-badge-cycling"), 
        "running": ("🏃‍♂️", "workout-badge-running"),
        "run": ("🏃‍♂️", "workout-badge-running"),
        "strength": ("💪", "workout-badge-strength"),
        "swim": ("🏊‍♂️", "workout-badge-cycling"),
        "other": ("⚡", "workout-badge-strength")
    }
    
    workout_lower = workout_type.lower()
    icon, css_class = badges.get(workout_lower, badges["other"])
    
    return f'<span class="{css_class}">{icon} {workout_type.title()}</span>'

def display_weekly_summary(summary):
    """Display weekly summary data with enhanced styling"""
    # Enhanced summary metrics with custom styling
    create_section_header("Weekly Training Summary", "📊")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        create_custom_metric("Total TSS", f"{summary.get('total_tss', 0):.1f}", "🎯", "blue")
    with col2:
        create_custom_metric("Training Hours", f"{summary.get('total_training_hours', 0):.1f}", "⏱️", "green") 
    with col3:
        create_custom_metric("Sessions", str(summary.get('sessions_completed', 0)), "🏃‍♂️", "orange")
    
    # Workout Types with badges
    workout_types = summary.get('workout_types', [])
    if workout_types:
        create_section_header("Workout Types", "🏋️‍♂️")
        badges_html = " ".join([create_workout_badge(wt) for wt in workout_types])
        st.markdown(badges_html, unsafe_allow_html=True)
    
    # Enhanced Daily Notes
    create_section_header("Daily Training Notes", "📝")
    qualitative_feedback = summary.get('qualitative_feedback', [])
    if qualitative_feedback and isinstance(qualitative_feedback, list):
        for note in qualitative_feedback:
            # Handle different data formats safely
            if isinstance(note, dict):
                # Get day and type with safe fallbacks
                day_label = str(note.get('day', 'Unknown Day'))
                type_label = str(note.get('type', 'Unknown Type'))
                
                with st.expander(f"{day_label} - {type_label}"):
                    # Handle various formats of feedback data
                    feedback = note.get('feedback', {})
                    if isinstance(feedback, dict):
                        # Process dictionary feedback
                        for key, value in feedback.items():
                            if value and key not in ('intervals', 'sections'):  # Skip special fields
                                # Convert values to string for display
                                if isinstance(value, (dict, list)):
                                    value = str(value)
                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                    elif isinstance(feedback, str):
                        # If feedback is a plain string
                        st.write(feedback)
                    elif feedback is not None:
                        # Any other format, convert to string
                        st.write(str(feedback))
            elif note is not None:
                # Handle case where the note itself isn't a dictionary
                st.write(str(note))
    else:
        st.info("No daily notes available for this period")

def display_fit_file_analysis(fit_file, workout_data):
    """Display FIT file analysis in a structured way with better None handling"""
    st.write(f"### {fit_file.name}")
    
    # Helper function to safely format numeric values
    def safe_format(value, format_str="{:.1f}", default="N/A"):
        if value is None:
            return default
        try:
            return format_str.format(float(value))
        except (ValueError, TypeError):
            return default
    
    # Create three columns for key metrics
    col1, col2, col3 = st.columns(3)
    
    if workout_data.get('metrics'):
        metrics = workout_data['metrics']
        with col1:
            st.metric("Duration (min)", 
                     safe_format(metrics.get('duration')))
        with col2:
            st.metric("TSS", 
                     safe_format(metrics.get('tss')))
        with col3:
            st.metric("Intensity Factor", 
                     safe_format(metrics.get('intensity'), "{:.2f}"))
        with col3:
            st.metric("RPE", 
                     safe_format(metrics.get('rpe'), "{:.1f}"))  # Display RPE value
    
    # Determine available data types
    has_power = bool(workout_data.get('power_metrics'))
    has_hr = bool(workout_data.get('hr_metrics'))
    
    # Create tabs based on available data
    tab_names = []
    if has_power:
        tab_names.append("Power Analysis")
    if has_hr:
        tab_names.append("Heart Rate Analysis")
    if has_power or has_hr:
        tab_names.append("Zone Distribution")
    tab_names.append("Summary")  # Always include Summary tab
    
    if not tab_names:
        st.info("No detailed metrics available for this workout type")
        with st.expander("View Raw Data"):
            st.json(workout_data)
        return
    
    tabs = st.tabs(tab_names)
    current_tab = 0
    
    # Power Analysis Tab
    if has_power:
        with tabs[current_tab]:
            metrics = workout_data['power_metrics']
            
            pcol1, pcol2 = st.columns(2)
            with pcol1:
                st.metric("Average Power", 
                         f"{safe_format(metrics.get('average_power'), '{:.0f}')}W")
                st.metric("Normalized Power", 
                         f"{safe_format(metrics.get('normalized_power'), '{:.0f}')}W")
            with pcol2:
                st.metric("Max Power", 
                         f"{safe_format(metrics.get('max_power'), '{:.0f}')}W")
                st.metric("Intensity Factor", 
                         safe_format(metrics.get('intensity_factor'), "{:.2f}"))
            
            if metrics.get('zones'):
                st.subheader("Power Zone Distribution")
                # Function to standardize zone display format
                def standardize_zone_key(key):
                    """Convert any zone format to a consistent display format"""
                    if isinstance(key, str) and key.lower().startswith('zone'):
                        # Already in a good format, just ensure consistent capitalization
                        return key
                    return key
                
                # Create dataframe with standardized zone names
                zones_df = pd.DataFrame(
                    [(standardize_zone_key(k), v) for k, v in metrics['zones'].items() if v is not None and v > 0],
                    columns=['Zone', 'Time %']
                )
                if not zones_df.empty:
                    zones_df = zones_df.sort_values('Zone')
                    st.bar_chart(zones_df.set_index('Zone'))
        current_tab += 1
    
    # Heart Rate Analysis Tab
    if has_hr:
        with tabs[current_tab]:
            metrics = workout_data['hr_metrics']
            
            hcol1, hcol2 = st.columns(2)
            with hcol1:
                st.metric("Average HR", 
                         f"{safe_format(metrics.get('average_hr'), '{:.0f}')} bpm")
                st.metric("Min HR", 
                         f"{safe_format(metrics.get('min_hr'), '{:.0f}')} bpm")
            with hcol2:
                st.metric("Max HR", 
                         f"{safe_format(metrics.get('max_hr'), '{:.0f}')} bpm")
            
            if metrics.get('zones'):
                st.subheader("Heart Rate Zone Distribution")
                # Function to standardize zone display format for heart rate zones
                def standardize_hr_zone_key(key):
                    """Convert any zone format to a consistent display format"""
                    if isinstance(key, str):
                        # Handle 'zone1' format
                        if key.lower().startswith('zone'):
                            if len(key) > 4 and key[4:5].isdigit() and key.lower() == f"zone{key[4:5]}":
                                zone_num = key[4:5]
                                # Map to standard format
                                zone_names = {
                                    '1': 'Zone 1 (Recovery)',
                                    '2': 'Zone 2 (Endurance)',
                                    '3': 'Zone 3 (Tempo)',
                                    '4': 'Zone 4 (Threshold)',
                                    '5': 'Zone 5 (Maximum)'
                                }
                                return zone_names.get(zone_num, f"Zone {zone_num}")
                            # Already in a fully defined format
                            return key
                    return key
                
                # Create dataframe with standardized zone names
                zones_df = pd.DataFrame(
                    [(standardize_hr_zone_key(k), v) for k, v in metrics['zones'].items() if v is not None and v > 0],
                    columns=['Zone', 'Time %']
                )
                if not zones_df.empty:
                    zones_df = zones_df.sort_values('Zone')
                    st.bar_chart(zones_df.set_index('Zone'))
        current_tab += 1
    
    # Zone Distribution Tab
    if has_power or has_hr:
        with tabs[current_tab]:
            col1, col2 = st.columns(2)
            
            if has_power and workout_data.get('power_metrics', {}).get('zones'):
                with col1:
                    st.subheader("Power Zones")
                    zones = workout_data['power_metrics']['zones']
                    # Function to standardize zone display format
                    def standardize_zone_key(key):
                        """Convert any zone format to a consistent display format"""
                        if isinstance(key, str) and key.lower().startswith('zone'):
                            # Already in a good format, just ensure consistent capitalization
                            return key
                        return key
                    
                    # Filter out None values and zeros
                    valid_zones = {standardize_zone_key(k): v for k, v in zones.items() 
                                  if v is not None and v > 0}
                    if valid_zones:
                        fig = px.pie(
                            values=list(valid_zones.values()),
                            names=list(valid_zones.keys()),
                            title="Power Zone Distribution"
                        )
                        st.plotly_chart(fig)
            
            if has_hr and workout_data.get('hr_metrics', {}).get('zones'):
                with col2:
                    st.subheader("Heart Rate Zones")
                    zones = workout_data['hr_metrics']['zones']
                    # Function to standardize zone display format for heart rate zones
                    def standardize_hr_zone_key(key):
                        """Convert any zone format to a consistent display format"""
                        if isinstance(key, str):
                            # Handle 'zone1' format
                            if key.lower().startswith('zone'):
                                if len(key) > 4 and key[4:5].isdigit() and key.lower() == f"zone{key[4:5]}":
                                    zone_num = key[4:5]
                                    # Map to standard format
                                    zone_names = {
                                        '1': 'Zone 1 (Recovery)',
                                        '2': 'Zone 2 (Endurance)',
                                        '3': 'Zone 3 (Tempo)',
                                        '4': 'Zone 4 (Threshold)',
                                        '5': 'Zone 5 (Maximum)'
                                    }
                                    return zone_names.get(zone_num, f"Zone {zone_num}")
                                # Already in a fully defined format
                                return key
                        return key
                    
                    # Filter out None values and zeros with standardized keys
                    valid_zones = {standardize_hr_zone_key(k): v for k, v in zones.items() 
                                  if v is not None and v > 0}
                    if valid_zones:
                        fig = px.pie(
                            values=list(valid_zones.values()),
                            names=list(valid_zones.keys()),
                            title="HR Zone Distribution"
                        )
                        st.plotly_chart(fig)
        current_tab += 1
    
    # Summary Tab (always last)
    with tabs[-1]:
        if workout_data.get('metrics'):
            st.subheader("Workout Summary")
            summary_data = {
                "Duration": f"{safe_format(workout_data['metrics'].get('duration'))} minutes",
                "TSS": safe_format(workout_data['metrics'].get('tss')),
                "Intensity": safe_format(workout_data['metrics'].get('intensity'), "{:.2f}"),
                "Start Time": workout_data.get('start_time', 'N/A')
            }
            
            for key, value in summary_data.items():
                st.write(f"**{key}:** {value}")
        
        with st.expander("View Raw Data"):
            st.json(workout_data)

def display_performance_analytics():
    """Display performance analytics with workout analysis, personal bests, and visualizations"""
    from src.utils.fit_file_analyzer import FitFileAnalyzer
    from src.utils.workout_visualizer import WorkoutVisualizer
    
    create_section_header("Performance Analytics", "🏆")
    
    st.markdown("""
    ### 📊 AI-Powered Workout Analysis & Personal Best Tracking
    
    **Automated Daily Analysis** with TrainingPeaks integration or manual FIT file upload:
    - 🤖 **AI Analysis**: Gemini-powered workout insights
    - 🏅 **Personal Bests**: Track your peak efforts with medals (🥇🥈🥉)
    - 📈 **Interactive Graphs**: Power curves, zone distribution, and more
    - 🔄 **Auto-Discovery**: Finds workouts from TrainingPeaks downloads automatically
    """)
    
    # Create tabs for different analytics sections
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Historical Data", "🏅 Personal Bests", "🔄 Auto Analysis", "📤 Manual Upload"])
    
    with tab1:
        from src.ui.tabs.historical_analysis import render_historical_analysis_tab
        render_historical_analysis_tab()
    
    with tab2:
        st.subheader("🏅 Your Personal Bests")
        
        try:
            from src.storage.database import WorkoutDatabase
            db = WorkoutDatabase('data/fitness_data.db')
            personal_bests = db.get_personal_bests(athlete_id='default')
            
            if personal_bests:
                # Define standard duration order (matches FitFileAnalyzer)
                duration_order = {
                    '30s': 1,
                    '1min': 2,
                    '3min': 3,
                    '5min': 4,
                    '10min': 5,
                    '20min': 6,
                    '45min': 7,
                    '60min': 8
                }
                
                # Filter to only valid durations, then sort by duration order
                valid_efforts = {k: v for k, v in personal_bests.items() if k in duration_order}
                sorted_efforts = sorted(
                    valid_efforts.items(),
                    key=lambda x: duration_order.get(x[0], 999)
                )
                
                # Display in a nice format
                for effort_type, bests in sorted_efforts:
                    st.markdown(f"#### {effort_type.upper().replace('_', ' ')}")
                    
                    cols = st.columns(3)
                    for i, best in enumerate(bests):
                        if i < 3:  # Only show top 3
                            with cols[i]:
                                medal = best.get('medal', '')
                                power = best.get('effort_value', 0)
                                date_achieved = best.get('achieved_date', 'Unknown')
                                
                                st.markdown(f"""
                                <div style="text-align: center; padding: 10px; border: 2px solid #ddd; border-radius: 10px;">
                                    <div style="font-size: 40px;">{medal}</div>
                                    <div style="font-size: 24px; font-weight: bold;">{power:.0f}W</div>
                                    <div style="font-size: 12px; color: #666;">{date_achieved}</div>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    st.markdown("---")
            else:
                st.info("No personal bests recorded yet. Upload a workout to start tracking!")
        
        except Exception as e:
            st.error(f"Error loading personal bests: {str(e)}")
    
    with tab3:
        st.subheader("🔄 Automated Daily Sync & Analysis")
        
        st.success("""
        **🎯 Complete Automation Active!**
        
        This feature provides end-to-end automation:
        1. 🔐 Logs into TrainingPeaks (headless browser)
        2. 📥 Downloads today's workout files
        3. 💾 Stores in database via API
        4. 🤖 Runs AI analysis with Gemini
        5. 🏅 Updates personal bests automatically
        6. 🧹 Cleans up temporary files
        """)
        
        st.markdown("""
        **Benefits:**
        - ✅ No manual file management
        - ✅ No downloads folder clutter
        - ✅ Automatic cleanup after processing
        - ✅ Scheduled for 10pm PST daily
        - ✅ Rate limiting respects API limits
        
        **Manual Trigger:** Click button below to run now  
        **Automated:** Configure cron job for nightly runs
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            analysis_ftp = st.number_input(
                "Your FTP (watts)",
                min_value=100,
                max_value=500,
                value=300,
                help="Your Functional Threshold Power"
            )
        
        with col2:
            analysis_date = st.date_input(
                "Run automation for date",
                value=datetime.now().date(),
                help="Select the date to sync and analyze"
            )
        
        # Manual trigger button
        if st.button("🚀 Run Complete Automation Now", type="primary", use_container_width=True):
            with st.spinner(f"🔄 Running TrainingPeaks sync & analysis for {analysis_date}..."):
                try:
                    from src.utils.daily_auto_sync_and_analyze import DailyAutoSyncAndAnalyze
                    
                    automation = DailyAutoSyncAndAnalyze(db_path='data/fitness_data.db')
                    
                    # Convert analysis_date to proper date object
                    target_date = analysis_date if isinstance(analysis_date, date) else analysis_date[0] if isinstance(analysis_date, tuple) else datetime.now().date()
                    
                    results = automation.run_daily_automation(
                        target_date=target_date,
                        ftp_watts=int(analysis_ftp),
                        cleanup=True
                    )
                    
                    # Display results
                    if results['workouts_analyzed'] > 0:
                        st.success(f"✅ Complete! Downloaded & analyzed {results['workouts_analyzed']} workout(s)")
                    elif results['fit_files_downloaded'] == 0:
                        st.warning(f"🔍 No workouts found on TrainingPeaks for {target_date}")
                    else:
                        st.error("❌ Downloaded workouts but analysis failed")
                    
                    # Metrics row
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Files Downloaded", results['fit_files_downloaded'])
                    with col2:
                        st.metric("Workouts Analyzed", results['workouts_analyzed'])
                    with col3:
                        st.metric("New Personal Bests", results['personal_bests'])
                    with col4:
                        st.metric("Errors", len(results['errors']))
                    
                    # Show summary info
                    if results['workouts_analyzed'] > 0:
                        st.markdown("### 📊 Workflow Summary")
                        st.info(f"""
                        **Completed steps:**
                        1. ✅ Logged into TrainingPeaks
                        2. ✅ Downloaded {results['fit_files_downloaded']} FIT file(s)
                        3. ✅ Stored in database
                        4. ✅ Analyzed with Gemini AI
                        5. ✅ Updated personal bests
                        6. ✅ Cleaned up temporary files
                        """)
                
                except ValueError as ve:
                    st.error(f"⚠️ {str(ve)}")
                    st.info("Make sure your GEMINI_API_KEY environment variable is set")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    import traceback
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
        
        st.markdown("---")
        
        # AI Model Management Section
        with st.expander("🤖 AI Model Management (Advanced)", expanded=False):
            st.markdown("""
            **Dynamic Model Discovery** ensures the system automatically uses available free Google Gemini models.
            
            As Google updates their model lineup, this keeps your analysis working without code changes.
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Refresh Available Models", help="Query Google's API for currently available free models"):
                    with st.spinner("Discovering models..."):
                        try:
                            from src.utils.gemini_model_discovery import GeminiModelDiscovery
                            
                            discovery = GeminiModelDiscovery()
                            free_models = discovery.get_free_models(force_refresh=True)
                            
                            st.success(f"✅ Found {len(free_models)} free models")
                            st.markdown("**Top 10 models:**")
                            for i, model in enumerate(free_models[:10], 1):
                                st.text(f"{i}. {model}")
                            
                            # Test for working model
                            with st.spinner("Testing model availability..."):
                                working_model = discovery.get_working_model()
                                if working_model:
                                    st.success(f"✅ Current best model: `{working_model}`")
                                else:
                                    st.error("❌ No working models found (may be quota limits)")
                        except Exception as e:
                            st.error(f"Error discovering models: {e}")
                
                if st.button("📋 View Model Cache", help="Show currently cached models"):
                    try:
                        from src.utils.gemini_model_discovery import GeminiModelDiscovery
                        import json
                        
                        discovery = GeminiModelDiscovery()
                        cache = discovery._load_cache()
                        
                        if cache:
                            st.success(f"✅ Cache from {cache['timestamp'][:19]}")
                            st.text(f"{len(cache['models'])} models cached")
                            with st.expander("Show all cached models"):
                                for model in cache['models']:
                                    st.text(f"• {model}")
                        else:
                            st.info("No cache found. Click 'Refresh Available Models' to create cache.")
                    except Exception as e:
                        st.error(f"Error loading cache: {e}")
            
            with col2:
                st.markdown("**Model Discovery Features:**")
                st.markdown("""
                - 🔍 Auto-discovers 30+ Gemini models
                - 📊 Prioritizes by speed/stability
                - 💾 Caches results for 24 hours
                - 🔄 Falls back to static list if API fails
                - ✅ Tests models for availability
                - 🆓 Uses only FREE tier models
                """)
                
                st.info("""
                **When to refresh:**
                - Getting model errors
                - Quota exhausted on all models
                - Google released new models
                - Haven't refreshed in >1 week
                """)
        
        st.markdown("---")
        st.markdown("### ⏰ Schedule Automatic Sync & Analysis (10pm PST)")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("""
            **Quick Setup:**
            
            ```bash
            ./setup_daily_automation.sh
            ```
            
            Then add to crontab (`crontab -e`):
            ```bash
            # Complete automation at 10pm PST
            0 22 * * * cd /Users/jacobrobinson/fitness_tracker && /Users/jacobrobinson/fitness_tracker/venv/bin/python -m src.utils.daily_auto_sync_and_analyze >> /Users/jacobrobinson/fitness_tracker/logs/daily_automation.log 2>&1
            ```
            """)
        
        with col2:
            st.success("""
            **Complete Workflow:**
            1. 🔐 TP Login
            2. 📥 Download
            3. 💾 Database
            4. 🤖 AI Analysis
            5. 🏅 PB Tracking
            6. 🧹 Cleanup
            """)
        
        with st.expander("🍎 Mac Closed Lid Options"):
            st.markdown("""
            **Running with laptop closed:**
            
            1. **Keep docked/open** (simplest)
            
            2. **Disable sleep when plugged in:**
               - System Settings → Lock Screen
               - Turn display off: Never (when plugged in)
            
            3. **Command line:**
               ```bash
               sudo pmset -c sleep 0
               ```
            
            **Note:** Some Macs may not run cron when lid is closed.  
            Alternative: Run on a server or use cloud automation.
            """)
    
    with tab4:
        st.subheader("Upload Workout FIT File")
        
        uploaded_file = st.file_uploader(
            "Choose a FIT file from Zwift, Garmin, Wahoo, etc.",
            type=['fit', 'gz'],
            help="Upload a .fit or .fit.gz file from your cycling computer or indoor trainer"
        )
        
        if uploaded_file is not None:
            try:
                # Read file content
                file_content = uploaded_file.read()
                
                # Get athlete FTP if available
                athlete_ftp = st.number_input(
                    "Your FTP (watts)",
                    min_value=100,
                    max_value=500,
                    value=258,
                    help="Your Functional Threshold Power in watts"
                )
                
                # Optional athlete notes
                athlete_notes = st.text_area(
                    "Workout Notes (optional)",
                    placeholder="How did this workout feel? Any specific observations?"
                )
                
                if st.button("🔍 Analyze Workout", type="primary"):
                    with st.spinner("Analyzing workout data..."):
                        # Initialize analyzer with free models
                        try:
                            analyzer = FitFileAnalyzer(use_dynamic_models=True)
                            visualizer = WorkoutVisualizer()
                            
                            # Analyze the workout
                            analysis_result = analyzer.analyze_workout(
                                file_content,
                                athlete_ftp=float(athlete_ftp),
                                athlete_notes=athlete_notes
                            )
                            
                            if analysis_result:
                                st.success("✅ Workout analyzed successfully!")
                                st.info("💰 Cost: $0 (using free Gemini models)")
                                
                                # Display parsed metrics
                                parsed_data = analysis_result['parsed_data']
                                peak_efforts = analysis_result['peak_efforts']
                                ai_analysis = analysis_result['ai_analysis']
                                
                                # Metrics overview
                                col1, col2, col3, col4 = st.columns(4)
                                
                                power_metrics = parsed_data.get('power_metrics', {})
                                hr_metrics = parsed_data.get('hr_metrics', {})
                                
                                with col1:
                                    st.metric(
                                        "Duration",
                                        f"{parsed_data.get('duration_hours', 0)*60:.0f} min"
                                    )
                                with col2:
                                    st.metric(
                                        "Avg Power",
                                        f"{power_metrics.get('average_power', 0):.0f}W"
                                    )
                                with col3:
                                    st.metric(
                                        "Normalized Power",
                                        f"{power_metrics.get('normalized_power', 0):.0f}W"
                                    )
                                with col4:
                                    st.metric(
                                        "TSS",
                                        f"{power_metrics.get('tss', 0):.0f}"
                                    )
                                
                                # AI Analysis
                                st.markdown("### 🤖 AI Workout Analysis")
                                st.markdown(ai_analysis)
                                
                                # Peak Efforts
                                if peak_efforts:
                                    st.markdown("### ⚡ Peak Efforts")
                                    
                                    # Display in columns
                                    effort_cols = st.columns(4)
                                    for idx, (effort_name, effort_data) in enumerate(peak_efforts.items()):
                                        col_idx = idx % 4
                                        with effort_cols[col_idx]:
                                            st.metric(
                                                effort_name.upper(),
                                                f"{effort_data['power']:.0f}W"
                                            )
                                
                                # Visualizations
                                st.markdown("### 📊 Workout Visualization")
                                
                                try:
                                    fig = visualizer.create_workout_dashboard(parsed_data, peak_efforts)
                                    st.plotly_chart(fig, use_container_width=True)
                                except Exception as viz_error:
                                    st.warning(f"Could not create visualization: {viz_error}")
                                
                                # Peak power curve
                                if peak_efforts:
                                    st.markdown("### ⚡ Peak Power Curve")
                                    try:
                                        power_curve_fig = visualizer.create_peak_power_curve(peak_efforts)
                                        st.plotly_chart(power_curve_fig, use_container_width=True)
                                    except Exception as curve_error:
                                        st.warning(f"Could not create power curve: {curve_error}")
                                
                                # Store in database option
                                st.markdown("---")
                                if st.button("💾 Save Analysis to Database"):
                                    try:
                                        db = WorkoutDatabase('data/fitness_data.db')
                                        
                                        # Store analysis
                                        analysis_id = db.store_workout_analysis(
                                            workout_id=None,
                                            fit_file_id=None,
                                            analysis_text=ai_analysis,
                                            model_used="gemini-2.0-flash-exp"
                                        )
                                        
                                        # Store personal bests
                                        workout_date = parsed_data.get('start_time', '')[:10]
                                        for effort_name, effort_data in peak_efforts.items():
                                            pb_id = db.store_personal_best(
                                                effort_type=effort_name,
                                                effort_value=effort_data['power'],
                                                achieved_date=workout_date,
                                                athlete_id='default'
                                            )
                                            if pb_id:
                                                st.success(f"🏆 New personal best for {effort_name}!")
                                        
                                        st.success(f"✅ Analysis saved! (ID: {analysis_id})")
                                    except Exception as save_error:
                                        st.error(f"Error saving to database: {save_error}")
                            else:
                                st.error("❌ Could not analyze workout file")
                        
                        except ValueError as ve:
                            st.error(f"⚠️ {str(ve)}")
                            st.info("Make sure your GEMINI_API_KEY environment variable is set")
                        except Exception as e:
                            st.error(f"❌ Error analyzing workout: {str(e)}")
                            import traceback
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())
            
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    


def display_workout_calendar():
    st.header("Workout Calendar")
    
    # Get current week number and date
    today = datetime.now().date()
    now = datetime.now()
    # Local variables may be a date or None after normalization
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # ================== SIDEBAR PANELS ==================
    # Quick Stats Panel
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📊 Current Week Stats")
        
        try:
            # Fetch current week's workouts
            week_response = requests.get(
                f"{API_URL}/proposed_workouts/week",
                params={
                    "start_date": start_of_week.strftime('%Y-%m-%d'),
                    "end_date": end_of_week.strftime('%Y-%m-%d')
                }
            )
            
            if week_response.status_code == 200:
                week_data = week_response.json()
                daily_workouts = week_data.get('daily_workouts', [])
                
                # Calculate stats
                total_workouts = len(daily_workouts)
                completed_workouts = sum(1 for w in daily_workouts if w.get('date') and datetime.strptime(w['date'], '%Y-%m-%d').date() < today)
                
                # Calculate TSS
                total_tss = 0
                for workout in daily_workouts:
                    intervals = workout.get('intervals', [])
                    if isinstance(intervals, list):
                        for interval in intervals:
                            if isinstance(interval, dict):
                                total_tss += interval.get('tss', 0) or 0
                
                # Get planned TSS range from weekly plan
                weekly_plan = week_data.get('weekly_plan', {})
                planned_tss_min = weekly_plan.get('plannedTSS_min', 0)
                planned_tss_max = weekly_plan.get('plannedTSS_max', 0)
                
                # Display metrics with green/yellow gradient styling
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%); 
                            padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem; color: white;'>
                    <div style='font-size: 0.9rem; opacity: 0.9;'>Total Workouts</div>
                    <div style='font-size: 1.8rem; font-weight: bold;'>{total_workouts}</div>
                    <div style='font-size: 0.8rem; opacity: 0.8;'>{completed_workouts} completed</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #a8e063 0%, #d4fc79 100%); 
                            padding: 1rem; border-radius: 10px; margin-bottom: 0.5rem; color: #2d5016;'>
                    <div style='font-size: 0.9rem; opacity: 0.9; font-weight: 600;'>Planned TSS</div>
                    <div style='font-size: 1.8rem; font-weight: bold;'>{planned_tss_min}-{planned_tss_max}</div>
                    <div style='font-size: 0.8rem; opacity: 0.8;'>Week {datetime.now().isocalendar()[1]}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Weekly focus if available
                if weekly_plan.get('notes'):
                    try:
                        notes = json.loads(weekly_plan['notes'])
                        week_focus = notes.get('weekFocus', '')
                        if week_focus:
                            st.markdown(f"""
                            <div style='background: linear-gradient(135deg, #f9ca24 0%, #f0932b 100%); 
                                        padding: 0.8rem; border-radius: 8px; color: white;'>
                                <div style='font-size: 0.8rem; opacity: 0.9;'>🎯 WEEK FOCUS</div>
                                <div style='font-size: 0.9rem; margin-top: 0.3rem;'>{week_focus}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    except:
                        pass
        except Exception as e:
            st.warning("Unable to load week stats")
        
        # Upcoming Workouts Panel
        st.markdown("---")
        st.markdown("### 📅 Upcoming This Week")
        
        try:
            # Get remaining workouts for the week
            upcoming_workouts = []
            for workout in daily_workouts:
                workout_date_str = workout.get('date')
                if workout_date_str:
                    workout_date = datetime.strptime(workout_date_str, '%Y-%m-%d')
                    # Include today and future workouts
                    if workout_date.date() >= today:
                        # Calculate duration - try plannedDuration first, then sum intervals
                        duration = workout.get('plannedDuration', 0)
                        if not duration:
                            # Calculate from intervals
                            intervals = workout.get('intervals', [])
                            if isinstance(intervals, list):
                                for interval in intervals:
                                    if isinstance(interval, dict):
                                        # Duration might be in seconds, convert to minutes
                                        interval_duration = interval.get('duration', 0)
                                        if interval_duration > 300:  # Likely in seconds
                                            duration += interval_duration / 60
                                        else:
                                            duration += interval_duration
                        
                        upcoming_workouts.append({
                            'date': workout_date,
                            'name': workout.get('name', 'Workout'),
                            'type': workout.get('type', 'unknown'),
                            'duration': int(duration) if duration else 0
                        })
            
            # Sort by date
            upcoming_workouts.sort(key=lambda x: x['date'])
            
            if upcoming_workouts:
                for workout in upcoming_workouts[:5]:  # Show max 5 upcoming
                    workout_type = workout['type'].lower()
                    icon = "🚴" if workout_type == "bike" else "💪" if workout_type == "strength" else "🏃" if workout_type == "run" else "🧘"
                    
                    # Determine if it's today
                    is_today = workout['date'].date() == today
                    bg_color = "linear-gradient(135deg, #56ab2f 0%, #a8e063 100%)" if is_today else "#f8fdf4"
                    text_color = "white" if is_today else "#2d5016"
                    
                    day_label = "Today" if is_today else workout['date'].strftime("%a")
                    
                    # Use full workout name - CSS will handle wrapping to 2 lines
                    workout_name = workout['name']
                    
                    st.markdown(f"""
                    <div style='background: {bg_color}; 
                                padding: 0.6rem; border-radius: 8px; margin-bottom: 0.5rem;
                                border: 2px solid {"#56ab2f" if is_today else "#e1e1e1"};'>
                        <div style='color: {text_color}; font-weight: 600; font-size: 0.85rem;'>
                            {icon} {day_label} • {workout['duration']}min
                        </div>
                        <div style='color: {text_color}; font-size: 0.75rem; opacity: 0.9; margin-top: 0.2rem;
                                    line-height: 1.4;
                                    max-height: 2.8em;
                                    overflow: hidden;
                                    word-wrap: break-word;
                                    display: -webkit-box;
                                    -webkit-line-clamp: 2;
                                    -webkit-box-orient: vertical;'>
                            {workout_name}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background: #f8fdf4; padding: 1rem; border-radius: 8px; 
                            text-align: center; color: #2d5016; opacity: 0.7;'>
                    <div style='font-size: 2rem;'>✅</div>
                    <div style='font-size: 0.85rem; margin-top: 0.5rem;'>All done for this week!</div>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.info("No upcoming workouts")
    
    # Date range selector with default to current week
    col1, col2 = st.columns(2)
    with col1:
        selected_week_start = st.date_input(
            "Week Start Date", 
            value=start_of_week
        )
    with col2:
        selected_week_end = st.date_input(
            "Week End Date", 
            value=end_of_week
        )

    # Normalize Streamlit date widget return values (can be date, datetime or a tuple when range-select is used)
    # Use the module-level helper below
    selected_week_start = _normalize_date_widget(selected_week_start)
    selected_week_end = _normalize_date_widget(selected_week_end)

    # Cast to concrete date type for static checkers (we validated above)
    selected_week_start = cast(date, selected_week_start)
    selected_week_end = cast(date, selected_week_end)

    # Validate normalized dates
    if selected_week_start is None or selected_week_end is None:
        st.warning("Please select a valid week start and end date.")
        return
    
    # Add help text about where data is stored
    with st.expander("About Workout Tracking Data"):
        st.markdown("""
        ### Where is my workout data saved?
        
        When you track your workout performance and click "Save Workout Data":
        
        1. Your data is saved in the database in the `workout_performance` table
        2. The data includes all sets, reps, weights, and notes you've entered
        3. This data is linked to the specific workout by ID and date
        4. Your saved workout performance data will be included in your weekly summaries
        5. You can view past performance in the Weekly Summary section
        
        Data is saved locally in your SQLite database file and isn't sent to any external servers.
        """)
    
    # Check if API is available
    try:
        # Simple check to see if API is up
        test_response = requests.get(f"{API_URL}/")
        if test_response.status_code != 200:
            st.error("Cannot connect to API server. Please ensure it's running.")
            return
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server. Please ensure it's running at {API_URL}/")
        return
    
    # Fetch proposed workouts for the selected week
    try:
        response = requests.get(
            f"{API_URL}/proposed_workouts/week",
            params={
                "start_date": selected_week_start.strftime('%Y-%m-%d') if selected_week_start else None,
                "end_date": selected_week_end.strftime('%Y-%m-%d') if selected_week_end else None
            }
        )
        
        if response.status_code != 200:
            st.error(f"Error fetching workouts: {response.text}")
            return
        
        workouts_data = response.json()
        
        # Display weekly overview
        if 'weekly_plan' in workouts_data and workouts_data['weekly_plan']:
            st.subheader("Weekly Plan Overview")
            weekly_plan = workouts_data['weekly_plan']
            
            cols = st.columns(3)
            with cols[0]:
                st.metric("Week Number", weekly_plan.get('weekNumber', 'N/A'))
            with cols[1]:
                st.metric("Planned TSS", f"{weekly_plan.get('plannedTSS_min', 0)}-{weekly_plan.get('plannedTSS_max', 0)}")
            with cols[2]:
                st.metric("Week Start", weekly_plan.get('startDate', 'N/A'))
            
            if weekly_plan.get('notes'):
                try:
                    notes = json.loads(weekly_plan['notes'])
                    st.info(f"**Weekly Focus:** {notes.get('weekFocus', '')}")
                    if notes.get('specialConsiderations'):
                        st.warning(f"**Special Considerations:** {notes.get('specialConsiderations', '')}")
                except Exception as e:
                    st.warning(f"Failed to parse weekly plan notes: {e}")
                    st.text(weekly_plan['notes'])
        
        # Create a mapping of date to workouts
        daily_workouts = {}
        for workout in workouts_data.get('daily_workouts', []):
            date_str = workout.get('date')
            if date_str:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                if date_obj not in daily_workouts:
                    daily_workouts[date_obj] = []
                daily_workouts[date_obj].append(workout)
        
        # Create tabs for each day of the week
        st.subheader("Daily Workouts")
        
        # Get all days in the selected range
        current_date = selected_week_start
        days = []
        while current_date <= selected_week_end:
            days.append(current_date)
            current_date += timedelta(days=1)
        
        # Create tabs for each day with unique formatted labels
        day_tabs = st.tabs([day.strftime("%a %d") for day in days])
        
        # Fill each day tab with workout information
        for i, day in enumerate(days):
            with day_tabs[i]:
                if day in daily_workouts:
                    # Display all workouts for this day
                    for j, workout in enumerate(daily_workouts[day]):
                        # Generate unique keys for all interactive elements based on day and workout
                        workout_id = workout.get('id', 0)
                        day_str = day.strftime("%Y%m%d")
                        unique_workout_key = f"{day_str}_{workout_id}_{j}"
                        
                        workout_type = workout.get('type', 'unknown').lower()
                        
                        # Different icons for different workout types
                        icon = "🚴" if workout_type == "bike" else "💪" if workout_type == "strength" else "🏃" if workout_type == "run" else "🧘" if workout_type == "yoga" else "📝"
                        
                        # Create a section for each workout
                        st.markdown(f"## {icon} {workout.get('name', 'Workout')}")
                        
                        # Basic workout info
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            # Create a unique container for each metric to avoid conflicts
                            duration_container = st.container()
                            duration_container.metric(
                                label="Duration", 
                                value=f"{workout.get('plannedDuration', 'N/A')} min"
                            )
                        with col2:
                            if workout.get('plannedTSS_min') and workout.get('plannedTSS_max'):
                                tss_container = st.container()
                                tss_container.metric(
                                    label="TSS",
                                    value=f"{workout.get('plannedTSS_min')}-{workout.get('plannedTSS_max')}"
                                )
                        with col3:
                            if workout.get('targetRPE_min') and workout.get('targetRPE_max'):
                                rpe_container = st.container()
                                rpe_container.metric(
                                    label="Target RPE",
                                    value=f"{workout.get('targetRPE_min')}-{workout.get('targetRPE_max')}"
                                )
                        
                        # Check if we already have performance data for this workout
                        try:
                            perf_response = requests.get(
                                f"{API_URL}/workout/performance",
                                params={
                                    "workout_id": workout_id,
                                    "workout_date": workout.get('date', '')
                                }
                            )
                            
                            if perf_response.status_code == 200 and 'performance_data' in perf_response.json():
                                st.success("🔄 You've already tracked this workout!")
                                view_key = f"view_{unique_workout_key}"
                                if st.button("View/Edit Tracking Data", key=view_key):
                                    # Just a placeholder
                                    st.info("This feature is coming soon! Currently, you can add new tracking data.")
                        except Exception as e:
                            # Log error but continue
                            print(f"Error checking performance data: {str(e)}")
                        
                        # Show workout details based on type with unique keys
                        if workout_type == "bike":
                            st.markdown("### Workout Details")
                            display_bike_workout(workout)
                        elif workout_type == "run":
                            st.markdown("### Workout Details")
                            display_run_workout(workout)
                        elif workout_type in ["strength", "yoga", "mobility", "other"]:
                            st.markdown("### Workout Details")
                            # Pass unique key to avoid duplicate widget keys
                            display_strength_workout_with_tracking(workout, unique_key=unique_workout_key)
                        
                        # Add a divider between workouts
                        if j < len(daily_workouts[day]) - 1:
                            st.divider()
                else:
                    st.info("Rest day")
    
    except Exception as e:
        st.error(f"Error loading calendar: {str(e)}")
        st.exception(e)  # This will show the full traceback

def display_bike_workout(workout):
    """Display bike workout intervals with comprehensive coaching notes"""
    
    # Display overall workout notes if available - enhanced with better formatting
    if workout.get('notes'):
        notes = workout.get('notes')
        
        # Parse notes if they're stored as JSON string
        if isinstance(notes, str):
            try:
                import json
                notes = json.loads(notes)
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, treat as a single string
                notes = [notes]
        
        if isinstance(notes, list) and notes:
            # Categorize notes for better presentation
            race_strategy_notes = []
            nutrition_notes = []
            power_pacing_notes = []
            recovery_notes = []
            general_notes = []
            
            for note in notes:
                note_lower = note.lower()
                if any(keyword in note_lower for keyword in ['race', 'strategy', 'scoring', 'power-up', 'tactic', 'contest', 'racing', 'points race']):
                    race_strategy_notes.append(note)
                elif any(keyword in note_lower for keyword in ['carb', 'nutrition', 'drink', 'electrolyte', 'hydrat', 'fuel']):
                    nutrition_notes.append(note)
                elif any(keyword in note_lower for keyword in ['hr', 'heart rate', 'bpm', 'power', 'watt', '%', 'ftp', 'threshold', 'tempo', 'zone']):
                    power_pacing_notes.append(note)
                elif any(keyword in note_lower for keyword in ['recovery', 'sleep', 'sauna', 'cool', 'rest', 'easy', 'maintenance', 'energy']):
                    recovery_notes.append(note)
                else:
                    general_notes.append(note)
            
            # Display categorized notes with better formatting
            if race_strategy_notes:
                with st.expander("🎯 Race Strategy & Mental Prep", expanded=False):
                    for note in race_strategy_notes:
                        if note.startswith(('RACE STRATEGY', 'TACTICAL')):
                            st.markdown(f"**{note}**")
                        else:
                            st.markdown(f"• {note}")
            
            if nutrition_notes:
                with st.expander("🥤 Nutrition & Fueling", expanded=False):
                    for note in nutrition_notes:
                        if note.startswith(('NUTRITION', 'PRE-RACE PREP')):
                            st.markdown(f"**{note}**")
                        else:
                            st.markdown(f"• {note}")
            
            if power_pacing_notes:
                with st.expander("⚡ Power & Heart Rate Guidelines", expanded=False):
                    for note in power_pacing_notes:
                        if note.startswith('POWER PACING'):
                            st.markdown(f"**{note}**")
                        else:
                            st.markdown(f"• {note}")
            
            if recovery_notes:
                with st.expander("😴 Recovery & Energy Management", expanded=False):
                    for note in recovery_notes:
                        if note.startswith('POST-RACE'):
                            st.markdown(f"**{note}**")
                        else:
                            st.markdown(f"• {note}")
            
            if general_notes:
                with st.expander("📝 Coaching Notes", expanded=True):
                    for note in general_notes:
                        # Check if it's a section header (ALL CAPS or starts with keywords)
                        if (note.isupper() and len(note) > 10) or note.startswith(('WARMUP', 'COOLDOWN', 'CRITICAL')):
                            st.markdown(f"**{note}**")
                        else:
                            st.markdown(f"• {note}")
        elif isinstance(notes, str) and notes.strip():
            # Single string note
            st.markdown("### 📝 Workout Notes")
            st.markdown(f"• {notes}")
        else:
            # Fallback for any other format
            st.markdown("### 📝 Workout Notes")
            st.markdown(f"{notes}")
    
    st.subheader("🏋️ Interval Structure")
    
    # Parse intervals from JSON string if needed
    intervals = workout.get('intervals')
    if isinstance(intervals, str):
        try:
            intervals = json.loads(intervals)
        except Exception as e:
            st.warning(f"Could not parse intervals data: {e}")
            return
    
    if not intervals:
        st.info("No interval data available")
        return
    
    # Display intervals as a table with enhanced power formatting
    intervals_data = []
    for i, interval in enumerate(intervals):
        interval_data = {
            "Name": interval.get('name', f"Interval {i+1}"),
            "Duration": f"{interval.get('duration', 0)/60:.1f} min" if interval.get('duration') else 'N/A',
        }
        
        # Handle different power target formats with better display
        power_target = interval.get('powerTarget', {})
        if isinstance(power_target, dict):
            if power_target.get('type') == 'percent_ftp':
                interval_data["Power"] = f"{power_target.get('value', 0)}% FTP"
            elif power_target.get('type') == 'watts':
                interval_data["Power"] = f"{power_target.get('value', 0)}W"
            elif 'start' in power_target and 'end' in power_target:
                start_value = power_target.get('start', {}).get('value', 0)
                end_value = power_target.get('end', {}).get('value', 0)
                interval_data["Power"] = f"{start_value}% → {end_value}% FTP"
            elif 'min' in power_target and 'max' in power_target:
                min_val = power_target.get('min', 0)
                max_val = power_target.get('max', 0)
                unit = power_target.get('unit', 'watts')
                if unit == 'watts':
                    if min_val == max_val:
                        interval_data["Power"] = f"{min_val}W"
                    else:
                        interval_data["Power"] = f"{min_val}-{max_val}W"
                else:
                    interval_data["Power"] = f"{min_val}-{max_val}% FTP"
            elif power_target.get('type') == 'range':
                min_val = power_target.get('min', 0)
                max_val = power_target.get('max', 0)
                unit = power_target.get('unit', 'watts')
                interval_data["Power"] = f"{min_val}-{max_val} {unit}"
        
        # Add cadence information if available
        cadence_target = interval.get('cadenceTarget', {})
        if cadence_target and isinstance(cadence_target, dict):
            cadence_min = cadence_target.get('min')
            cadence_max = cadence_target.get('max')
            if cadence_min and cadence_max:
                interval_data["Cadence"] = f"{cadence_min}-{cadence_max} RPM"
            else:
                interval_data["Cadence"] = "Free choice"
        else:
            interval_data["Cadence"] = "Free choice"
        
        intervals_data.append(interval_data)
    
    # Create DataFrame and display as table
    if intervals_data:
        intervals_df = pd.DataFrame(intervals_data)
        st.table(intervals_df)

def display_run_workout(workout):
    """Display run workout with sections and detailed guidance"""
    
    # Display overall workout notes with enhanced formatting
    if workout.get('notes'):
        notes = workout.get('notes')
        if isinstance(notes, list):
            # Categorize run notes for better presentation
            hr_notes = []
            pacing_notes = []
            recovery_notes = []
            general_notes = []
            
            for note in notes:
                note_lower = note.lower()
                if any(keyword in note_lower for keyword in ['hr', 'heart rate', 'bpm', 'zone']):
                    hr_notes.append(note)
                elif any(keyword in note_lower for keyword in ['pace', 'breathing', 'nose', 'speed']):
                    pacing_notes.append(note)
                elif any(keyword in note_lower for keyword in ['recovery', 'stretch', 'cooldown', 'post-run']):
                    recovery_notes.append(note)
                else:
                    general_notes.append(note)
            
            # Display categorized notes with better formatting
            if hr_notes:
                with st.expander("💗 Heart Rate Guidelines", expanded=True):
                    for note in hr_notes:
                        if note.startswith('HR TARGET'):
                            st.markdown(f"**{note}**")
                        else:
                            st.markdown(f"• {note}")
            
            if pacing_notes:
                with st.expander("🏃 Pacing & Breathing", expanded=True):
                    for note in pacing_notes:
                        st.markdown(f"• {note}")
            
            if recovery_notes:
                with st.expander("🧘 Recovery Protocol", expanded=False):
                    for note in recovery_notes:
                        if note.startswith('POST-RUN'):
                            st.markdown(f"**{note}**")
                        else:
                            st.markdown(f"• {note}")
            
            if general_notes:
                with st.expander("📝 General Notes", expanded=True):
                    for note in general_notes:
                        if note.startswith('PURPOSE') or note.startswith('CRITICAL'):
                            st.markdown(f"**{note}**")
                        else:
                            st.markdown(f"• {note}")
        else:
            st.markdown("### 📝 Workout Notes")
            st.markdown(f"{notes}")
    
    st.subheader("🏃 Run Structure")
    
    # Parse sections from JSON string if needed
    sections = workout.get('sections')
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception as e:
            st.warning(f"Could not parse sections data: {e}")
            return
    
    if not sections:
        st.info("No section data available")
        return
    
    # Display sections with enhanced formatting
    st.markdown("### Run Sections")
    for i, section in enumerate(sections):
        section_name = section.get('name', f"Section {i+1}")
        with st.expander(f"{section_name}", expanded=True):
            # Display section duration/distance
            if section.get('duration'):
                st.markdown(f"**Duration:** {section.get('duration')} min")
            if section.get('distance'):
                distance = section.get('distance', {})
                if isinstance(distance, dict):
                    value = distance.get('value', 'N/A')
                    unit = distance.get('unit', 'km')
                    st.markdown(f"**Distance:** {value} {unit}")
            
            # Display target pace
            target_pace = section.get('targetPace')
            if target_pace:
                st.markdown("**Target Pace:**")
                if isinstance(target_pace, dict):
                    if target_pace.get('description'):
                        st.markdown(f"{target_pace.get('description')}")
                    
                    # Display detailed notes
                    if target_pace.get('notes'):
                        notes = target_pace.get('notes')
                        st.markdown("**Guidance:**")
                        if isinstance(notes, list):
                            for note in notes:
                                st.markdown(f"- {note}")
                        else:
                            st.markdown(f"- {notes}")
                else:
                    st.markdown(f"{target_pace}")


def display_strength_workout_with_tracking(workout, unique_key=""):
    """Display strength workout with integrated tracking for each exercise"""
    st.subheader("Workout Routine")
    
    # Mets theme colors
    METS_BLUE = "#002D72"
    METS_ORANGE = "#FF5910"
    METS_LIGHT_BLUE = "#E6E6FA"
    
    # Parse sections from JSON string if needed
    sections = workout.get('sections', [])
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except Exception as e:
            st.warning(f"Could not parse workout sections data: {str(e)}")
            sections = []
    
    # If no sections but has notes, display notes as workout description
    if not sections:
        notes = workout.get('notes', '')
        if notes:
            st.markdown("### Workout Description")
            # Split notes into lines and format as bullet points if multiple lines
            note_lines = [line.strip() for line in notes.split('\n') if line.strip()]
            if len(note_lines) > 1:
                for line in note_lines:
                    st.markdown(f"- {line}")
            else:
                st.info(notes)
        else:
            st.info("No workout details available")
        return
    
    # Create a form for tracking data with a unique key
    form = st.form(key=f"workout_tracking_{unique_key}_{workout.get('id', '')}")
    with form:
        
        # Process each section
        for section_idx, section in enumerate(sections):
            section_name = section.get('name', f"Section {section_idx+1}")
            
            # Add visual distinction for section types (based on name heuristics)
            section_type = ""
            if "warm" in section_name.lower():
                section_color = "#FFE1B4"  # Light orange for warmup
                section_type = "🔥 WARMUP"
            elif "cool" in section_name.lower():
                section_color = "#D6EAF8"  # Light blue for cooldown
                section_type = "❄️ COOLDOWN"
            elif "circuit" in section_name.lower():
                section_color = "#D5F5E3"  # Light green for circuit
                section_type = "⚡ CIRCUIT"
            elif "finish" in section_name.lower():
                section_color = "#FADBD8"  # Light red for finisher
                section_type = "🏁 FINISHER"
            elif workout.get('type', '').lower() == "mobility":
                section_color = "#E8DAEF"  # Light purple for mobility
                section_type = "🧘 MOBILITY"
            else:
                section_color = METS_LIGHT_BLUE  # Mets light blue for other sections
                section_type = "💪 STRENGTH"
            
            # Section header with Mets-themed styling
            st.markdown(f"""
            <div style="background-color: {section_color}; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid {METS_BLUE};">
                <h3 style="margin:0; color: {METS_BLUE};">{section_name} <span style="font-size:0.8em; font-weight:normal; color: {METS_ORANGE};">{section_type}</span></h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Section info
            info_cols = st.columns(2)
            with info_cols[0]:
                if section.get('duration'):
                    duration_val = section.get('duration')
                    # Section duration is always in minutes for mobility/strength
                    st.write(f"**Section Duration:** {duration_val} min")
            with info_cols[1]:
                if section.get('rounds'):
                    st.write(f"**Rounds:** {section.get('rounds')}")
            
            # Process exercises in this section
            exercises = section.get('exercises', [])
            for ex_idx, exercise in enumerate(exercises):
                ex_name = exercise.get('name', f"Exercise {ex_idx+1}")
                
                # Create a unique key for this exercise including the outer unique key
                ex_key = f"{unique_key}_s{section_idx}_e{ex_idx}"
                
                # Exercise header with Mets-themed styling
                st.markdown(f"""
                <div style="background-color: {METS_LIGHT_BLUE}; padding: 8px; border-radius: 5px; margin: 10px 0; border-left: 4px solid {METS_ORANGE};">
                    <h4 style="margin:0; color: {METS_BLUE};">{ex_name}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                # Add exercise reference button
                import urllib.parse
                search_query = urllib.parse.quote(f"{ex_name} exercise demonstration")
                search_url = f"https://www.google.com/search?q={search_query}&tbm=isch"
                st.markdown(f"<a href='{search_url}' target='_blank' style='color: {METS_ORANGE};'>🔍 Look up exercise reference</a>", unsafe_allow_html=True)
                
                # Display exercise details in columns
                detail_cols = st.columns([1, 1])
                
                # Column 1: Display exercise guidance
                with detail_cols[0]:
                    # Display cues with better formatting and Mets styling
                    if exercise.get('cues'):
                        cues = exercise.get('cues')
                        st.markdown(f"**<span style='color: {METS_BLUE}'>🎯 Cues:</span>**", unsafe_allow_html=True)
                        if isinstance(cues, list):
                            cue_text = ""
                            for cue in cues:
                                cue_text += f"- {cue}\n"
                            st.markdown(cue_text)
                        else:
                            st.markdown(f"- {cues}")
                    
                    # Display modifications if present
                    if exercise.get('modifications'):
                        mods = exercise.get('modifications')
                        st.markdown(f"**<span style='color: {METS_BLUE}'>🔄 Modifications:</span>**", unsafe_allow_html=True)
                        if isinstance(mods, list):
                            mod_text = ""
                            for mod in mods:
                                mod_text += f"- {mod}\n"
                            st.markdown(mod_text)
                        else:
                            st.markdown(f"- {mods}")
                    
                    # Display focus if present
                    if exercise.get('focus'):
                        focus = exercise.get('focus')
                        st.markdown(f"**<span style='color: {METS_BLUE}'>🔍 Focus:</span>**", unsafe_allow_html=True)
                        if isinstance(focus, list):
                            focus_text = ""
                            for f in focus:
                                focus_text += f"- {f}\n"
                            st.markdown(focus_text)
                        else:
                            st.markdown(f"- {focus}")
                
                # Column 2: Display any additional exercise notes
                with detail_cols[1]:
                    # Display general notes
                    if exercise.get('notes'):
                        notes = exercise.get('notes')
                        st.markdown(f"**<span style='color: {METS_BLUE}'>📝 Notes:</span>**", unsafe_allow_html=True)
                        if isinstance(notes, list):
                            notes_text = ""
                            for note in notes:
                                notes_text += f"- {note}\n"
                            st.markdown(notes_text)
                        else:
                            st.markdown(f"- {notes}")
                
                # Process sets with interleaved tracking
                sets = exercise.get('sets', [])
                if sets:
                    # Check for rounds at the section level
                    rounds = section.get('rounds', 1)
                    
                    # Create columns for headers with Mets-themed styling
                    st.markdown(f"""
                    <div style="background-color: {METS_LIGHT_BLUE}; padding: 5px; border-radius: 3px; margin: 10px 0; border-left: 4px solid {METS_ORANGE};">
                        <div class="row-widget stRow">
                            <div class="row" style="display: flex; align-items: center;">
                                <div style="flex: 1; color: {METS_BLUE};"><strong>Set Details</strong></div>
                                <div style="flex: 1; color: {METS_BLUE};"><strong>Target</strong></div>
                                <div style="flex: 2; color: {METS_BLUE};"><strong>Your Performance</strong></div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Instead of showing sets per round, just display each set once
                    for set_idx, set_info in enumerate(sets):
                        # Generate a unique key for this set
                        set_key = f"{ex_key}_set{set_idx}"
                        
                        # Create a container for this set with visual separation
                        set_container = st.container()
                        with set_container:
                            # Create a row with 3 columns for this set
                            cols = st.columns([1, 1, 2])
                            
                            # Column 1: Set number with Mets styling
                            with cols[0]:
                                # Replace "Set X" with more meaningful information - just show the number of sets
                                if set_info.get('sets'):
                                    st.markdown(f"**<span style='color: {METS_BLUE}'>Perform: {set_info.get('sets')} sets</span>**", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"**<span style='color: {METS_BLUE}'>Perform: 1 set</span>**", unsafe_allow_html=True)
                                
                                # Show rest information if available
                                if set_info.get('restBetweenSets'):
                                    rest_time = set_info.get('restBetweenSets')
                                    st.markdown(f"**Rest:** {rest_time}s between sets")
                                
                                # If rounds are specified at the section level, show that as well
                                if rounds > 1:
                                    st.markdown(f"**Rounds:** {rounds}")
                            
                            # Column 2: Target details
                            with cols[1]:
                                # Format target information
                                target_desc = []

                                # Handle reps
                                if set_info.get('reps'):
                                    reps_text = f"Reps: {set_info.get('reps')}"
                                    if set_info.get('perSide', False):
                                        reps_text += " (each side)"
                                    target_desc.append(reps_text)
                                elif set_info.get('targetReps'):
                                    target = set_info.get('targetReps', {})
                                    if isinstance(target, dict):
                                        if target.get('value'):
                                            target_reps = str(target.get('value'))
                                        else:
                                            target_reps = f"{target.get('min', 0)}-{target.get('max', 0)}"
                                        reps_text = f"Reps: {target_reps}"
                                        if target.get('perSide', False):
                                            reps_text += " (each side)"
                                        target_desc.append(reps_text)

                                # Handle duration
                                if set_info.get('duration'):
                                    duration = set_info.get('duration')
                                    per_side = set_info.get('perSide', False)
                                    
                                    # If perSide is true, show both per-side and total time
                                    if per_side:
                                        per_side_time = duration
                                        total_time = duration * 2
                                        if total_time >= 60:
                                            target_desc.append(f"Duration: {total_time//60}m {total_time%60}s total ({per_side_time//60}m {per_side_time%60}s per side)")
                                        else:
                                            target_desc.append(f"Duration: {total_time}s total ({per_side_time}s per side)")
                                    else:
                                        if duration >= 60:
                                            target_desc.append(f"Duration: {duration//60}m {duration%60}s")
                                        else:
                                            target_desc.append(f"Duration: {duration}s")

                                # Handle work/rest timing
                                if set_info.get('workTime'):
                                    target_desc.append(f"Work: {set_info.get('workTime')}s")
                                if set_info.get('restTime'):
                                    target_desc.append(f"Rest: {set_info.get('restTime')}s")

                                # Handle weight
                                if set_info.get('weight'):
                                    weight = set_info.get('weight')
                                    weight_text = "Weight: "
                                    
                                    if isinstance(weight, dict):
                                        if weight.get('value'):
                                            weight_text += f"{weight.get('value')}"
                                        elif weight.get('min') is not None and weight.get('max') is not None:
                                            weight_text += f"{weight.get('min')}-{weight.get('max')}"
                                        elif weight.get('unit'):
                                            weight_text += f"{weight.get('unit')}"
                                        else:
                                            weight_text += "as shown"
                                    else:
                                        weight_text += f"{weight}"
                                    
                                    # Add units if not already present
                                    if isinstance(weight, dict) and weight.get('unit'):
                                        weight_text += f" {weight.get('unit')}"
                                    elif not str(weight).endswith('lbs') and not str(weight).lower() == 'bodyweight':
                                        weight_text += " lbs"
                                    
                                    target_desc.append(weight_text)

                                # Handle tempo and direction
                                if set_info.get('tempo'):
                                    target_desc.append(f"Tempo: {set_info.get('tempo')}")
                                if set_info.get('direction'):
                                    target_desc.append(f"Direction: {set_info.get('direction')}")

                                # Display all target information
                                st.text("\n".join(target_desc))
                                
                                # Display notes if available
                                if set_info.get('notes'):
                                    st.markdown("**Notes:**")
                                    if isinstance(set_info.get('notes'), list):
                                        for note in set_info.get('notes'):
                                            st.markdown(f"- {note}")
                                    else:
                                        st.markdown(f"- {set_info.get('notes')}")
                                
                                # Display cues if available
                                if set_info.get('cues'):
                                    st.markdown("**Cues:**")
                                    if isinstance(set_info.get('cues'), list):
                                        for cue in set_info.get('cues'):
                                            st.markdown(f"- {cue}")
                                    else:
                                        st.markdown(f"- {set_info.get('cues')}")
                    
                            # Column 3: Performance tracking
                            with cols[2]:
                                # Create a container for tracking fields
                                tracking_container = st.container()
                                
                                # Add tracking fields based on the type of set
                                if set_info.get('reps') or set_info.get('targetReps'):
                                    tracking_container.number_input(
                                        "Reps Completed",
                                        min_value=0,
                                        max_value=100,
                                        key=f"reps_{set_key}"
                                    )
                                
                                if set_info.get('weight'):
                                    tracking_container.number_input(
                                        "Weight Used (lbs)",
                                        min_value=0,
                                        max_value=1000,
                                        key=f"weight_{set_key}"
                                    )
                                
                                if set_info.get('duration') or set_info.get('workTime'):
                                    tracking_container.number_input(
                                        "Duration (seconds)",
                                        min_value=0,
                                        max_value=3600,
                                        key=f"duration_{set_key}"
                                    )
                                # Add notes field for each set with minimum height
                                tracking_container.text_area(
                                    "Notes",
                                    key=f"notes_{set_key}",
                                    height=100  # Increased from 50 to meet minimum requirement
                                )
                            
                            # Add a subtle divider between sets
                            st.markdown(f"<hr style='border: 1px solid {METS_LIGHT_BLUE}; margin: 10px 0;'/>", unsafe_allow_html=True)
                    
                    # Add a divider between exercises
                    st.markdown(f"<hr style='border: 2px solid {METS_BLUE}; margin: 20px 0;'/>", unsafe_allow_html=True)
        
        # Add proper form submit button
        submitted = form.form_submit_button("Save Workout Data", use_container_width=True)
        if submitted:
            st.success("Workout data saved successfully!")

def create_workout_timer():
    """Create a persistent timer for workout tracking with audio alerts"""
    # Initialize timer state if not already in session state
    if 'timer_running' not in st.session_state:
        st.session_state.timer_running = False
        st.session_state.timer_duration = 60
        st.session_state.rest_duration = 30
        st.session_state.timer_mode = "Work"  # "Work" or "Rest"
        st.session_state.timer_end_time = None
        st.session_state.last_update = datetime.now()
        st.session_state.should_play_audio = False
        st.session_state.audio_type = None  # "work_complete" or "rest_complete"
        st.session_state.cycles_completed = 0  # Track completed cycles
    
    # Create a container that will always be visible and fixed at the top
    with st.sidebar:
        st.markdown("### 🕒 Workout Timer")
        st.markdown("*The clock doesn't care about your excuses.*")
        
        # Work/Rest cycle settings
        col1, col2 = st.columns(2)
        
        with col1:
            work_duration = st.number_input("Work (seconds)", min_value=5, max_value=600, 
                                          value=st.session_state.timer_duration, step=5, 
                                          key="work_duration_input")
            st.session_state.timer_duration = work_duration
        
        with col2:
            rest_duration = st.number_input("Rest (seconds)", min_value=5, max_value=600, 
                                          value=st.session_state.rest_duration, step=5,
                                          key="rest_duration_input")
            st.session_state.rest_duration = rest_duration
        
        # Add audio option
        enable_audio = st.checkbox("Enable sound alerts", value=True)
        
        # Controls row
        col1, col2 = st.columns(2)
        with col1:
            if not st.session_state.timer_running:
                if st.button("▶️ Start", key="start_timer_button", use_container_width=True):
                    # Explicitly set all timer state
                    current_time = datetime.now()
                    st.session_state.timer_running = True
                    st.session_state.timer_end_time = current_time + timedelta(seconds=work_duration)
                    st.session_state.timer_mode = "Work"
                    st.session_state.last_update = current_time
                    st.session_state.should_play_audio = False
                    st.session_state.cycles_completed = 0
                    # Force immediate rerun to start the timer
                    st.rerun()
            else:
                if st.button("⏹️ Stop", key="stop_timer_button", use_container_width=True):
                    st.session_state.timer_running = False
                    st.rerun()
        
        with col2:
            if st.button("🔄 Reset", key="reset_timer_button", use_container_width=True):
                st.session_state.timer_running = False
                st.session_state.timer_mode = "Work"
                st.session_state.should_play_audio = False
                st.session_state.cycles_completed = 0
                st.rerun()
        
        # Display cycles completed
        if st.session_state.cycles_completed > 0:
            st.caption(f"Completed cycles: {st.session_state.cycles_completed}")
        
        # Current mode indicator with color coding
        mode_color = "#4CAF50" if st.session_state.timer_mode == "Work" else "#FF9800"
        st.markdown(f"""
            <div style='background-color: {mode_color}; padding: 10px; border-radius: 5px; text-align: center; color: white; font-weight: bold;'>
                {st.session_state.timer_mode} MODE
            </div>
        """, unsafe_allow_html=True)
        
        # Audio element (browsers require user interaction to play audio on a page)
        # We use a simple beep sound for now
        if enable_audio and st.session_state.should_play_audio:
            audio_type = st.session_state.audio_type
            if audio_type == "work_complete":
                st.markdown("""
                <audio autoplay>
                    <source src="data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBTGH0fPTgjMGHm7A7+OZSA0PVK7n77FdGAg+ltryxnMpBSl+zPLaizsIGGS57OihUBELTKXh8bllHgU2jdXzzn0vBSF1xe/glEILElyx6OyrWBUIQ5zd8sFuJAUuhM/z1YU2Bhxqvu7mnEoODlGq5PC1YBoGPJPY88p2KwUme8rx3I4+CRZiturqpVITC0mi4PK8aB8GM4nU8tGAMQYfcsLu45ZFDBFYr+ftrFoXCECY3PLEcSYELIHO8diJOQgZaLvt559NEAxPp+PwtmMcBjiP1/PMeS0GI3fH8N2RQAoUXrTp66hVFApGnt/yvmwhBTCG0fPTgjQGHW/A7eSaRw0PVK7m77BeGQc9ltvyxnUoBSh+zPDaizsIGGS57OihUBELTKXh8bllHgU1jdT0z30vBSJ0xe/glEILElyx6OyrWRUIRJve8sFuJAUug8/z1oU2Bhxqvu7mnEoPDVKq5PC1YRoGPJLY88p3KgUme8rx3I4+CRVht+rqpVMSC0mi4PG9aB8GMojU8tGAMQYfccPu45ZFDBBYr+ftrVkYB0CZ3PLEcSYGK4DN8tiIOQgZaLzt559NFAxPpuPxtmQcBjiP1/PMeywGI3fH8N2RQAoUXrTp66hWFApGnt/yv2wiBDCG0PTTgzQHHG/A7eSaSA0PVK3m77BeGQc9ltrzxnQpBSh+zPDaizsIF2S57OihUREKTKXh8blmHgY1jdT0z30vBSF0xe/glUILElyw6eyrWRYIRJzd8sFvJQQug8/z1oY2Bhxqvu3mnEoPDVKp5PC1YRoGOpPY88p3KwUmecnw3Y4+CRVht+rqpVQSCkmi4PG9aB8GM4jT89GAMgUfccPu45ZFDBBYr+ftrVkYB0CZ3PLEcScFLIHO8diJOAgZaLvt559NEAxPpuPxtmQdBTiP1/PMey0FI3fH8N2RQAoUXrTp66hWFApGnt/yv2wiBDCG0PTTgzQHHG3A7eSaSA0PVK3m77BeGQc+ltvyxnQpBSh9zPDbizsIF2W57OihUREKTKXh8blmHgY1jdT0z30vBSF0xO/glUILElyw6eyrWRYIRJzd8sFvJQQug8/z1oY3BRxqvu3mnEoPDVKp5PC1YRoGOpPY88p3KwUmecnw3Y4+CRVht+rqpVQSCkmi4PG9aB8GM4jT89GAMgUfccPu45ZFDBBYr+ftrVkYB0CZ3PLEcScFLIHO8diJOAgYaLvt559OEAxPpuPxtmQdBTeP1/PMey0FI3fH8N2RQQkUXrTo66hWFQlGnt/yv2wiBDCG0PTTgzUGHG3A7eSaSA0PVK3m77BeGQc+ltrzyHQpBSh9zPDbizsIF2W57OiiUBAKTKXi8blmHgY1jdT0z34wBCF0xO/glUILElux6eyrWRYIRJzd8sFvJQQug8/z1oY3BRxqvu3mnEoPDVKp5PC1YRoGOpPY88p3KwUmecnw3Y4/CBVht+rqpVQSCkmi4PG9aSAFM4jT89GAMgUfccPu45ZGCxBYr+ftrVkYB0CZ3PLEcScFLIHO8diJOAgYaLvt559OEAxPpuPxtmQdBTeP1/PMey0FI3fH8N2RQQkUXrTo66hWFQlGnt/yv2wiBDCG0PTTgzUGHG3A7eSaSA4PVK3m77BeGQc+ltrzyHQpBSh9zPDbizsIF2W57OiiUBAKTKXi8blmHgY1jdT0z34wBCF0xO/glUILElux6eyrWRYIRJzd8sFvJQQug8/z1oY3BRxqvu3mnEoPDVKp5PC1YRoGOpPY88p3KwUmecnw3Y4/CBVht+rqpVQSCkmi4PG9aSAFM4jT89GAMgUfccPu45ZGCxBYr+ftrVkYB0CZ3PLEcScFLIHO8diJOAgYaLvt559OEAxPpuPxtmQdBTeP1/PMey0FI3fH8N2RQQkUXrTo66hWFQlGnt/yv2wiBDCG0PTTgzUGHG3A7eSaSA4PVK3m77BeGQc+ltrzyHQpBSh9zPDbi0MIFmS46+mjTw==">
                </audio>
                """, unsafe_allow_html=True)
            elif audio_type == "rest_complete":
                st.markdown("""
                <audio autoplay>
                    <source src="data:audio/wav;base64,UklGRl43AABXQVZFZm10IBAAAAABAAEARKwAAESsAAABAAgAZGF0YWY3AAAAAAEBAQECAgMEBQcICAoLDQ8SFBcaHSEkKCwvMzc7QEVKS09TVFZYXF9jZ2pucHN2eXt9f4GDhYaIioyOkZOWmZygo6eqrbCztbcwNjk7PD5AQkVKUVpkbnd4enuFiJGWm6Cio6WmqKqsra+wsbKys7S0tbW1tra1tLS0tLOysrGwsK+vrq6tra2trq6vsbK1t7q9wMPHys7S1tnc3+Ll6Ojs7fHy8/T09fX19fX19PPy8fDu7ezr6ejo5+fm5uXl5OTj4+Li4uHh4eHh4eHi4uPk5OXm5+jp6uvs7e3u7u/v7+/v7+7u7u3t7Ozr6urp6Ofm5eTj4uHg39/e3dzb2tnY19bV1NTT0tLR0dDQz9DO0M/Pz9DP0NHS0tPT1NTV1tfY2dna29vc3d3e39/g4ODh4eHi4uLi4uPj4+Pk5OTk5OXl5eXl5eXm5ubm5ubm5ubm5ebm5eXl5eXk5OTk4+Pj4+Pi4uLi4eHh4eHg4ODg4ODf39/f39/f39/f3+Df4ODg4ODg4ODg4eHh4eHh4eHi4uLi4uPj4+Pk5OTk5OTl5eXl5ebm5ubm5ubm5ubm5ubm5ubm5eXl5eXl5eXk5OTk5OTk4+Pj4+Pj4+Pi4uLi4uLi4uLi4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uPi4uLi4uLi4uLi4uLi4uLi4uLi4uLi4uPj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTk5OTl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm5ubm6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ojo6Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+fn5+f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f4CAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCg=">
                </audio>
                """, unsafe_allow_html=True)
            
            # Reset audio state
            st.session_state.should_play_audio = False
            
        # Calculate and display time remaining if timer is running
        if st.session_state.timer_running and st.session_state.timer_end_time:
            now = datetime.now()
            time_remaining = max(0, (st.session_state.timer_end_time - now).total_seconds())
            
            # Display progress bar and time
            current_duration = st.session_state.timer_duration if st.session_state.timer_mode == "Work" else st.session_state.rest_duration
            progress = 1.0 - (time_remaining / current_duration)
            st.progress(progress)
            # Use ceiling instead of floor to show the current second we're in
            time_display = math.ceil(time_remaining) if time_remaining > 0 else 0
            st.markdown(f"<h2 style='text-align: center;'>{time_display}s</h2>", unsafe_allow_html=True)
            
            # Check if timer has ended
            if time_remaining <= 0:
                if st.session_state.timer_mode == "Work":
                    # Switch from Work to Rest
                    st.session_state.timer_mode = "Rest"
                    st.session_state.timer_end_time = datetime.now() + timedelta(seconds=rest_duration)
                    # Set audio to play on next update
                    st.session_state.should_play_audio = enable_audio
                    st.session_state.audio_type = "work_complete"
                    # Show visual notification
                    st.warning("⏰ Work period complete! Switching to REST mode")
                else:
                    # Switch from Rest to Work
                    st.session_state.timer_mode = "Work"
                    st.session_state.timer_end_time = datetime.now() + timedelta(seconds=work_duration)
                    # Increment the cycle counter
                    st.session_state.cycles_completed += 1
                    # Set audio to play on next update
                    st.session_state.should_play_audio = enable_audio
                    st.session_state.audio_type = "rest_complete"
                    # Show visual notification
                    st.success("⏰ Rest period complete! Switching to WORK mode")
                
                # Force rerun immediately to update the timer
                st.rerun()
            
            # Debug info to help troubleshoot
            # st.caption(f"Time remaining: {time_remaining:.1f}s, Last update: {(now - st.session_state.last_update).total_seconds():.1f}s ago")
            
            # Only update UI if sufficient time has passed (to avoid excessive reruns)
            # but ensure we always update at least once per second
            time_since_update = (now - st.session_state.last_update).total_seconds()
            if time_since_update >= 0.25:  # Update more frequently (4 times per second)
                st.session_state.last_update = now
                
                # Always rerun while timer is running (don't check time_remaining)
                st.rerun()
        else:
            # Show empty progress bar when not running
            st.progress(0.0)
            if not st.session_state.timer_running:
                st.markdown("<p style='text-align: center; color: gray;'>Timer not running</p>", unsafe_allow_html=True)
    
    # Return the timer state for reference
    return st.session_state.timer_running


def _normalize_date_widget(d: Any) -> Optional[date]:
    """Normalize Streamlit date widget return values to a date or None.

    Streamlit date_input may return a date, a datetime, or a tuple/list when a range
    is selected. This helper converts those into a single date or None.
    """
    if d is None:
        return None
    # If a range is returned, take the first element
    if isinstance(d, (tuple, list)):
        d = d[0] if d else None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return None

# Configure the page
st.set_page_config(
    page_title="Fitness Tracker",
    page_icon="🏃‍♂️",
    layout="wide"
)

# Initialize session state
if 'current_view' not in st.session_state:
    st.session_state['current_view'] = 'dashboard'
if 'show_notes_form' not in st.session_state:
    st.session_state.show_notes_form = False
if 'current_summary' not in st.session_state:
    st.session_state.current_summary = None
if 'notes_saved' not in st.session_state:
    st.session_state.notes_saved = False

def display_ai_coach():
    """AI Coach page - interactive AI coaching session"""
    create_section_header("AI Coach - Personalized Training Intelligence", "🤖")
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; color: white;'>
        <h3 style='margin: 0 0 0.5rem 0; color: white;'>🧠 AI-Powered Coaching</h3>
        <p style='margin: 0; opacity: 0.9;'>
            Get personalized training insights and workout plans based on your actual performance data,
            sleep quality, and recovery metrics. The AI learns from your training history and maintains
            week-over-week context.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # How it Works
    st.markdown("""
    <div style='background: #f8f9fa; padding: 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; border-left: 5px solid #667eea;'>
        <h4 style='margin-top: 0; color: #667eea;'>📖 How It Works</h4>
        <ol style='margin-bottom: 0; padding-left: 1.5rem; color: #333;'>
            <li style='color: #333;'><strong style='color: #333;'>Select a Completed Week</strong> - Choose dates for a week you've already trained (e.g., last week)</li>
            <li style='color: #333;'><strong style='color: #333;'>Add Context</strong> - (Optional) Share your upcoming schedule, goals, and feedback from the completed week</li>
            <li style='color: #333;'><strong style='color: #333;'>Generate Analysis</strong> - AI reviews your actual workout data, performance trends, and recovery metrics</li>
            <li style='color: #333;'><strong style='color: #333;'>Generate Workout Plan</strong> - AI creates a personalized 7-day plan for the week <em>following</em> your completed week</li>
            <li style='color: #333;'><strong style='color: #333;'>Save & Train</strong> - Save the plan to your database and automatically generate Zwift workout files</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for AI Coach
    if 'ai_analysis' not in st.session_state:
        st.session_state.ai_analysis = None
    if 'ai_workout_plan' not in st.session_state:
        st.session_state.ai_workout_plan = None
    if 'ai_week_selected' not in st.session_state:
        st.session_state.ai_week_selected = None
    
    # Week selection
    st.markdown("### 📅 Step 1: Select Completed Training Week")
    st.markdown("*Choose a week you've already trained - AI will analyze this data and plan your next week*")
    col1, col2 = st.columns(2)
    
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    with col1:
        ai_start_date = st.date_input(
            "Week Start Date",
            value=start_of_week,
            key="ai_start_date"
        )
    with col2:
        ai_end_date = st.date_input(
            "Week End Date",
            value=end_of_week,
            key="ai_end_date"
        )
    
    # Normalize dates
    ai_start_date = _normalize_date_widget(ai_start_date)
    ai_end_date = _normalize_date_widget(ai_end_date)
    
    if ai_start_date is None or ai_end_date is None:
        st.warning("Please select valid dates")
        return
    
    # User Context Input
    st.markdown("### 💭 Step 2: Provide Context (Optional but Recommended)")
    st.markdown("*Help the AI understand your situation better - reference your completed week and upcoming schedule*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        schedule_constraints = st.text_area(
            "📅 Upcoming Week Schedule & Constraints",
            placeholder="e.g., Tuesday evening race, Thursday travel day, Saturday 3-hour ride available, Sunday long run planned...",
            help="Share your schedule for the UPCOMING week - races, travel, available training times, conflicts",
            key="ai_schedule",
            height=120
        )
        
        training_focus = st.text_area(
            "🎯 Training Focus & Goals",
            placeholder="e.g., Building base for spring gravel events, improving FTP, preparing for XC skiing season...",
            help="What are your current training goals and focus areas?",
            key="ai_focus",
            height=120
        )
    
    with col2:
        week_feedback = st.text_area(
            "🗣️ Completed Week - Feedback & Feelings",
            placeholder="e.g., Tuesday's intervals felt strong, sleep quality was excellent Mon-Wed, needed extra recovery Friday, ready for harder efforts...",
            help="How did you feel during the COMPLETED week you selected above? Any notable observations about performance, recovery, or energy levels?",
            key="ai_feedback",
            height=120
        )
        
        st.markdown("""
        <div style='background: #f0f8ff; padding: 1rem; border-radius: 8px; border-left: 4px solid #667eea;'>
            <strong style='color: #667eea;'>💡 Tip:</strong> <span style='color: #333;'>The more context you provide, the better the AI can tailor its recommendations
            to your specific situation!</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Soreness and Fatigue Assessment
    st.markdown("---")
    st.markdown("### 🏥 Soreness & Fatigue Assessment (Optional)")
    st.markdown("*Help the AI understand your recovery state - especially useful when device metrics don't match how you feel*")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🦵 Muscle Soreness")
        
        # Quick selection for common soreness areas
        st.markdown("##### Select Sore Areas")
        soreness_areas = {
            "Quads": st.checkbox("Quads", key="ai_soreness_quads"),
            "Hamstrings": st.checkbox("Hamstrings", key="ai_soreness_hamstrings"),
            "Calves": st.checkbox("Calves", key="ai_soreness_calves"),
            "Lower Back": st.checkbox("Lower Back", key="ai_soreness_lower_back"),
            "Upper Back": st.checkbox("Upper Back", key="ai_soreness_upper_back"),
            "Core": st.checkbox("Core", key="ai_soreness_core"),
            "Other": st.checkbox("Other", key="ai_soreness_other")
        }
        
        # Soreness severity slider
        soreness_severity = st.slider(
            "Overall Soreness Level",
            min_value=1,
            max_value=5,
            value=1,
            help="1 = No soreness, 5 = Severe soreness",
            key="ai_soreness_severity"
        )
        
        # Additional soreness details
        muscle_soreness_details = st.text_area(
            "Additional Soreness Details",
            placeholder="e.g., Lower back particularly tight after Wednesday's long ride, felt better after Friday's mobility session...",
            help="Describe any specific patterns, triggers, or recovery observations",
            height=100,
            key="ai_soreness_details"
        )
    
    with col2:
        st.markdown("#### 😴 Fatigue Assessment")
        
        # Energy levels throughout the day
        st.markdown("##### Energy Pattern")
        energy_pattern = st.selectbox(
            "Select your typical energy pattern this week",
            options=[
                "Consistent energy throughout the day",
                "Strong in morning, declining later",
                "Low in morning, improving later",
                "Fluctuating throughout the day",
                "Consistently low energy",
                "Consistently high energy"
            ],
            key="ai_energy_pattern"
        )
        
        # Fatigue impact areas
        st.markdown("##### Fatigue Impact")
        fatigue_impacts = {
            "Sleep Quality": st.checkbox("Affected Sleep Quality", key="ai_fatigue_sleep"),
            "Workout Performance": st.checkbox("Affected Workout Performance", key="ai_fatigue_workout"),
            "Daily Activities": st.checkbox("Affected Daily Activities", key="ai_fatigue_daily"),
            "Mental Focus": st.checkbox("Affected Mental Focus", key="ai_fatigue_mental"),
            "Recovery Time": st.checkbox("Needed Extra Recovery Time", key="ai_fatigue_recovery")
        }
        
        # Additional fatigue details
        fatigue_details = st.text_area(
            "Additional Fatigue Details",
            placeholder="e.g., Needed 2-hour nap after Saturday's 4-hour ride, Garmin showed 40% energy but felt completely exhausted...",
            help="Describe any mismatch between device metrics and how you actually felt",
            height=100,
            key="ai_fatigue_details"
        )
    
    # Check if week changed
    week_key = f"{ai_start_date}_{ai_end_date}"
    if st.session_state.ai_week_selected != week_key:
        st.session_state.ai_analysis = None
        st.session_state.ai_workout_plan = None
        st.session_state.ai_week_selected = week_key
    
    # Step 1: Generate Analysis
    st.markdown("---")
    st.markdown("### 📊 Step 3: Generate Weekly Analysis")
    st.markdown("*AI will analyze your completed week's workout data, performance metrics, and recovery trends*")
    
    # Model selection for analysis
    st.markdown("**Select AI Model:**")
    analysis_model_choice = st.radio(
        "Analysis Model",
        options=["Claude Haiku 4.5 (Fast & Cheap - $0.008/week)", "Claude Sonnet 4.5 (Best Quality - $0.066/week)", "Gemini Flash (Free, Rate Limited)"],
        index=0,
        help="Haiku is 8x cheaper than Sonnet and excellent for analysis. Sonnet provides maximum quality. Gemini is free but limited to 10 requests per minute.",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("🔍 Generate AI Analysis", type="primary", use_container_width=True):
            with st.spinner("🤖 AI is analyzing your training week... This may take 10-30 seconds..."):
                try:
                    # Prepare user context
                    user_context = {}
                    if schedule_constraints:
                        user_context['schedule_constraints'] = schedule_constraints
                    if training_focus:
                        user_context['training_focus'] = training_focus
                    if week_feedback:
                        user_context['week_feedback'] = week_feedback
                        
                        # Auto-update coaching notes from athlete feedback
                        # This captures milestones, goal changes, FTP updates, etc.
                        try:
                            from utils.ai_coach_engine import AICoachEngine
                            temp_coach = AICoachEngine()
                            updates = temp_coach.coaching_notes.auto_update_from_feedback(
                                athlete_feedback=week_feedback,
                                week_number=None  # Will be set when we have week number
                            )
                            if any(updates.values()):
                                st.info(f"📝 Auto-updated coaching notes from your feedback: "
                                       f"{len(updates['achievements'])} achievements, "
                                       f"{len(updates['goals_updated'])} goal updates, "
                                       f"{len(updates['observations'])} observations")
                        except Exception as e:
                            # Don't fail if auto-update has issues
                            pass
                    
                    # Add soreness assessment to user context
                    sore_areas = [area for area, checked in soreness_areas.items() if checked]
                    if sore_areas or soreness_severity > 1 or muscle_soreness_details:
                        muscle_soreness = f"Severity: {soreness_severity}/5\n"
                        if sore_areas:
                            muscle_soreness += f"Areas: {', '.join(sore_areas)}\n"
                        if muscle_soreness_details:
                            muscle_soreness += f"Details: {muscle_soreness_details}"
                        user_context['muscle_soreness_patterns'] = muscle_soreness
                    
                    # Add fatigue assessment to user context
                    impact_areas = [area for area, checked in fatigue_impacts.items() if checked]
                    if energy_pattern != "Consistent energy throughout the day" or impact_areas or fatigue_details:
                        general_fatigue = f"Energy Pattern: {energy_pattern}\n"
                        if impact_areas:
                            general_fatigue += f"Impact Areas: {', '.join(impact_areas)}\n"
                        if fatigue_details:
                            general_fatigue += f"Details: {fatigue_details}"
                        user_context['general_fatigue_level'] = general_fatigue
                    
                    # Call analyze API (you'll need to create this endpoint)
                    import sys, os
                    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if parent_dir not in sys.path:
                        sys.path.insert(0, parent_dir)
                    
                    from utils.ai_coach_engine import AICoachEngine, AIModel
                    from storage.database import WorkoutDatabase
                    
                    # Use selected model for analysis
                    if "Haiku" in analysis_model_choice:
                        analysis_model = AIModel.CLAUDE_HAIKU
                    elif "Sonnet" in analysis_model_choice:
                        analysis_model = AIModel.CLAUDE_SONNET
                    else:
                        analysis_model = AIModel.GEMINI_FREE
                    
                    coach = AICoachEngine(model=analysis_model)
                    db = WorkoutDatabase()
                    
                    # Get weekly summary
                    weekly_summary = db.generate_weekly_summary(
                        ai_start_date.isoformat(),
                        ai_end_date.isoformat()
                    )
                    
                    if not weekly_summary:
                        st.error("No training data found for this week")
                        return
                    
                    # Generate analysis
                    analysis, metadata = coach.analyze_week(
                        weekly_summary=weekly_summary,
                        user_context=user_context if user_context else None
                    )
                    
                    st.session_state.ai_analysis = analysis
                    st.session_state.ai_metadata = metadata
                    
                    # Extract and save continuity
                    continuity = coach.extract_coaching_continuity(analysis, weekly_summary)
                    if continuity and all(key in continuity for key in ['key_observations', 'progression_notes', 'areas_to_monitor', 'next_week_priorities']):
                        coach.coaching_notes.add_coaching_continuity(
                            week_start_date=continuity.get('week_start_date', ai_start_date),
                            week_end_date=continuity.get('week_end_date', ai_end_date),
                            week_number=continuity.get('week_number', 0),
                            key_observations=continuity['key_observations'],
                            progression_notes=continuity['progression_notes'],
                            areas_to_monitor=continuity['areas_to_monitor'],
                            next_week_priorities=continuity['next_week_priorities'],
                            recurring_schedule=continuity.get('recurring_schedule')
                        )
                    else:
                        print("⚠️  Continuity extraction incomplete - skipping save")
                    
                    st.success("✅ Analysis complete!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error generating analysis: {str(e)}")
                    import traceback
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())
    
    with col2:
        if st.session_state.ai_analysis:
            st.markdown(f"""
            <div style='background: #e8f5e9; padding: 0.5rem; border-radius: 5px; text-align: center;'>
                <small>✅ Analysis Ready</small>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        if st.session_state.ai_analysis and 'ai_metadata' in st.session_state:
            cost = st.session_state.ai_metadata.get('cost', 0)
            st.markdown(f"""
            <div style='background: #fff3e0; padding: 0.5rem; border-radius: 5px; text-align: center;'>
                <small>💰 ${cost:.4f}</small>
            </div>
            """, unsafe_allow_html=True)
    
    # Display analysis
    if st.session_state.ai_analysis:
        st.markdown("#### 📝 AI Analysis")
        with st.expander("View Full Analysis", expanded=True):
            st.markdown(st.session_state.ai_analysis)
        
        # Step 2: Generate Workout Plan
        st.markdown("---")
        st.markdown("### 🏋️ Step 4: Generate Next Week's Workout Plan")
        st.markdown("*AI will create a personalized 7-day plan for the week following your completed week*")
        
        # Model selection for workout generation
        st.markdown("**Select AI Model for Workout Generation:**")
        generation_model_choice = st.radio(
            "Generation Model",
            options=["Claude Sonnet 4.5 (Recommended - $0.156/week)", "Claude Haiku 4.5 (Budget - $0.021/week)", "Gemini Flash (Free)"],
            index=0,
            help="Sonnet 4.5 is best for accurate structured workouts and duration calculations. Haiku is cheaper but still very good. Gemini is free but may have rate limits.",
            horizontal=True,
            label_visibility="collapsed"
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            if st.button("📅 Generate Workout Plan", type="primary", use_container_width=True):
                with st.spinner("🤖 AI is creating your personalized workout plan... This may take 10-30 seconds..."):
                    try:
                        from utils.ai_coach_engine import AICoachEngine, AIModel
                        from storage.database import WorkoutDatabase
                        
                        # Use selected model for generation
                        if "Haiku" in generation_model_choice:
                            generation_model = AIModel.CLAUDE_HAIKU
                        elif "Sonnet" in generation_model_choice:
                            generation_model = AIModel.CLAUDE_SONNET
                        else:
                            generation_model = AIModel.GEMINI_FREE
                        
                        coach = AICoachEngine(model=generation_model)
                        db = WorkoutDatabase()
                        
                        # Get weekly summary again
                        weekly_summary = db.generate_weekly_summary(
                            ai_start_date.isoformat(),
                            ai_end_date.isoformat()
                        )
                        
                        # Prepare user context
                        user_context = {}
                        if schedule_constraints:
                            user_context['schedule_constraints'] = schedule_constraints
                        if training_focus:
                            user_context['training_focus'] = training_focus
                        if week_feedback:
                            user_context['week_feedback'] = week_feedback
                        
                        # Generate workout plan
                        workout_plan, plan_metadata = coach.generate_workout_plan(
                            weekly_summary=weekly_summary,
                            analysis=st.session_state.ai_analysis,
                            user_context=user_context if user_context else None
                        )
                        
                        st.session_state.ai_workout_plan = workout_plan
                        st.session_state.ai_plan_metadata = plan_metadata
                        
                        st.success("✅ Workout plan generated!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error generating workout plan: {str(e)}")
                        import traceback
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())
        
        with col2:
            if st.session_state.ai_workout_plan:
                st.markdown(f"""
                <div style='background: #e8f5e9; padding: 0.5rem; border-radius: 5px; text-align: center;'>
                    <small>✅ Plan Ready</small>
                </div>
                """, unsafe_allow_html=True)
        
        with col3:
            if st.session_state.ai_workout_plan and 'ai_plan_metadata' in st.session_state:
                cost = st.session_state.ai_plan_metadata.get('cost', 0)
                st.markdown(f"""
                <div style='background: #fff3e0; padding: 0.5rem; border-radius: 5px; text-align: center;'>
                    <small>💰 ${cost:.4f}</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Display workout plan
        if st.session_state.ai_workout_plan:
            st.markdown("#### 📋 7-Day Workout Plan")
            
            plan = st.session_state.ai_workout_plan
            
            # Display plan overview
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Week", plan.get('weekNumber', 'N/A'))
            with col2:
                st.metric("FTP", f"{plan.get('ftp', 0)}W")
            with col3:
                # Handle TSS as either number or dict with min/max
                planned_tss = plan.get('plannedTSS', 'N/A')
                if isinstance(planned_tss, dict):
                    tss_min = planned_tss.get('min', 0)
                    tss_max = planned_tss.get('max', 0)
                    st.metric("Planned TSS", f"{tss_min}-{tss_max}")
                else:
                    st.metric("Planned TSS", planned_tss)
            
            # Display plan notes
            if plan.get('notes'):
                st.info(f"**Week Focus:** {plan['notes']}")
            
            # Display daily workouts
            days = plan.get('days', [])
            if days:
                st.markdown("#### Daily Workouts")
                
                for day in days:
                    day_num = day.get('dayNumber', 0)
                    workouts = day.get('workouts', [])
                    
                    if not workouts:
                        # Rest day
                        st.markdown(f"**Day {day_num}:** 🧘 Rest")
                        continue
                    
                    # Display each workout for this day
                    for workout in workouts:
                        workout_type = workout.get('type', 'unknown')
                        icon = "🚴" if workout_type == "bike" else "🏃" if workout_type == "run" else "💪" if workout_type == "strength" else "🧘"
                        
                        workout_name = workout.get('name', 'Workout')
                        workout_duration = workout.get('plannedDuration', 0)
                        
                        with st.expander(f"{icon} Day {day_num}: {workout_name} - {workout_duration}min"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(f"**Type:** {workout_type.title()}")
                                st.markdown(f"**Duration:** {workout_duration} min")
                            with col2:
                                # Handle TSS as dict with min/max
                                planned_tss = workout.get('plannedTSS', {})
                                if isinstance(planned_tss, dict):
                                    tss_min = planned_tss.get('min', 0)
                                    tss_max = planned_tss.get('max', 0)
                                    st.markdown(f"**TSS:** {tss_min}-{tss_max}")
                                else:
                                    st.markdown(f"**TSS:** {planned_tss}")
                                
                                # Handle RPE as dict with min/max
                                target_rpe = workout.get('targetRPE', {})
                                if isinstance(target_rpe, dict):
                                    rpe_min = target_rpe.get('min', 0)
                                    rpe_max = target_rpe.get('max', 0)
                                    st.markdown(f"**RPE:** {rpe_min}-{rpe_max}/10")
                                else:
                                    st.markdown(f"**RPE:** {target_rpe}/10")
                            with col3:
                                st.markdown(f"**Date:** {day.get('date', 'N/A')}")
                            
                            # Display notes
                            notes = workout.get('notes', [])
                            if notes:
                                st.markdown("**Notes:**")
                                for note in notes:
                                    st.markdown(f"- {note}")
                            
                            # Display intervals if available
                            intervals = workout.get('intervals', [])
                            if intervals:
                                st.markdown("**Intervals:**")
                                for interval in intervals:
                                    interval_name = interval.get('name', 'Interval')
                                    interval_duration = interval.get('duration', 0) // 60  # Convert seconds to minutes
                                    
                                    # Handle power target (can be range, percent, or ramp)
                                    power_target = interval.get('powerTarget', {})
                                    power_str = "N/A"
                                    if isinstance(power_target, dict):
                                        if power_target.get('type') == 'range':
                                            power_min = power_target.get('min', 0)
                                            power_max = power_target.get('max', 0)
                                            power_str = f"{power_min}-{power_max}W"
                                        elif 'start' in power_target and 'end' in power_target:
                                            # Handle both dict format and direct value format
                                            start_val = power_target['start']
                                            end_val = power_target['end']
                                            if isinstance(start_val, dict):
                                                start_pct = start_val.get('value', 0)
                                                end_pct = end_val.get('value', 0)
                                            else:
                                                start_pct = start_val
                                                end_pct = end_val
                                            power_str = f"{start_pct}%-{end_pct}% FTP"
                                    
                                    st.markdown(f"  - **{interval_name}**: {interval_duration}min @ {power_str}")
            
            # Save to proposed workouts
            st.markdown("---")
            st.markdown("### 💾 Step 5: Save & Export")
            st.markdown("*Save this plan to your database and automatically generate Zwift workout files*")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Plan to Proposed Workouts & Generate Zwift Files", type="primary", use_container_width=True):
                    with st.spinner("💾 Saving plan to database and generating Zwift files..."):
                        try:
                            from utils.ai_coach_engine import AICoachEngine, AIModel
                            import os
                            
                            coach = AICoachEngine(model=AIModel.GEMINI_FREE)
                            
                            # Get Zwift output directory from environment and expand ~ to home directory
                            zwift_dir = os.getenv('ZWIFT_WORKOUTS_DIR', "~/Documents/Zwift/Workouts/6870291")
                            zwift_dir = os.path.expanduser(zwift_dir)  # Expand ~ to full home path
                            
                            # Save plan and generate Zwift files
                            # Use the start date from the AI-generated plan, not the UI input
                            # (AI calculates next week's Monday correctly)
                            plan_start_date = st.session_state.ai_workout_plan.get('startDate')
                            success, message, zwift_files = coach.save_plan_to_database(
                                workout_plan=st.session_state.ai_workout_plan,
                                start_date=plan_start_date,
                                output_dir=zwift_dir
                            )
                            
                            if success:
                                st.success(f"✅ {message}")
                                
                                # Show Zwift files if any were generated
                                if zwift_files:
                                    st.markdown("#### 🚴 Generated Zwift Workout Files:")
                                    for zfile in zwift_files:
                                        st.markdown(f"- `{zfile}`")
                                    st.info(f"📁 Files saved to: `{zwift_dir}`")
                                else:
                                    st.info("ℹ️  No cycling workouts to generate Zwift files for (only Run/Strength/Mobility workouts)")
                                
                                # Show next steps
                                st.markdown("""
                                <div style='background: #e8f5e9; padding: 1rem; border-radius: 8px; margin-top: 1rem; border-left: 4px solid #4caf50;'>
                                    <strong>✅ Next Steps:</strong><br>
                                    • View your plan in <strong>📋 Proposed Workouts</strong> tab<br>
                                    • Zwift files are ready in your Zwift workouts folder<br>
                                    • Track your progress throughout the week!
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.error(f"❌ {message}")
                                
                        except Exception as e:
                            st.error(f"Error saving plan: {str(e)}")
                            import traceback
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())
            
            with col2:
                st.markdown("""
                <div style='background: #fff3e0; padding: 1rem; border-radius: 8px; border-left: 4px solid #ff9800;'>
                    <strong>💡 What This Does:</strong><br>
                    • Saves 7-day plan to database<br>
                    • Generates .zwo files for cycling workouts<br>
                    • Files appear in Zwift app automatically<br>
                    • Plan visible in Proposed Workouts tab
                </div>
                """, unsafe_allow_html=True)

def display_session_comparison_page():
    """Session Comparison page - compare similar workouts to track progress"""
    from src.utils.workout_comparator import WorkoutComparator
    from src.ui.components.session_comparison import (
        display_session_comparison,
        display_similar_workouts_list,
        display_find_similar_ui
    )
    
    create_section_header("Session Comparison - Track Your Progress", "🔄")
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; color: white;'>
        <h3 style='margin: 0 0 0.5rem 0; color: white;'>🔍 Compare Similar Workouts</h3>
        <p style='margin: 0; opacity: 0.9;'>
            Find similar workouts from your training history and compare them side-by-side to track
            progress, identify improvements, and understand how your fitness is developing over time.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Fetch cycling workouts with analyses
    try:
        response = requests.get(f"{API_URL}/workouts/with-analyses")
        if response.status_code != 200:
            st.error("Error fetching workout data")
            return
        
        workouts = response.json()
        
        # Filter to cycling workouts only (have TSS/power data)
        cycling_workouts = [
            w for w in workouts 
            if 'Zwift' in w.get('workout_title', '') or 'Bike' in w.get('workout_title', '')
        ]
        
        if not cycling_workouts:
            st.warning("No cycling workouts with analyses found. Please run batch sync to analyze your workouts first.")
            st.info("💡 Go to **Import Data** → **Batch Sync & Analysis** to analyze your cycling workouts.")
            return
        
        # Create DataFrame for easier manipulation
        workouts_df = pd.DataFrame(cycling_workouts)
        
        st.success(f"✅ Found {len(cycling_workouts)} analyzed cycling workouts")
        
        # Show comparison mode selector
        mode = st.radio(
            "Comparison Mode:",
            ["🔍 Find Similar Workouts", "⚖️ Compare Two Specific Workouts"],
            horizontal=True
        )
        
        st.markdown("---")
        
        if mode == "🔍 Find Similar Workouts":
            # Find similar workouts mode
            selected_idx, min_similarity, max_results = display_find_similar_ui(workouts_df)
            
            if st.button("🔎 Find Similar Workouts", type="primary"):
                target_workout = cycling_workouts[selected_idx]
                
                # Initialize comparator
                comparator = WorkoutComparator()
                
                # Find similar workouts
                with st.spinner("Analyzing workout similarities..."):
                    similar_workouts = comparator.find_similar_workouts(
                        target_workout,
                        cycling_workouts,
                        min_similarity=min_similarity,
                        max_results=max_results
                    )
                
                if similar_workouts:
                    display_similar_workouts_list(similar_workouts, target_workout['workout_day'])
                    
                    # If we have matches, show detailed comparison for the top match
                    if similar_workouts:
                        st.markdown("---")
                        st.markdown("### 📊 Detailed Comparison (Top Match)")
                        
                        top_match_workout, top_similarity = similar_workouts[0]
                        
                        # Perform detailed comparison
                        comparison = comparator.compare_workouts_detailed(
                            target_workout,
                            top_match_workout
                        )
                        
                        # Display the comparison
                        display_session_comparison(
                            target_workout,
                            top_match_workout,
                            comparison
                        )
                else:
                    st.info(f"No workouts found with similarity ≥ {min_similarity}%. Try lowering the threshold.")
        
        else:
            # Compare two specific workouts mode
            st.markdown("### Select Two Workouts to Compare")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Workout 1** (Recent)")
                # Use workout_name if available (from proposed workout matching), otherwise fall back to title
                # Clean up filenames if they appear
                def format_workout_name(row):
                    name = row.get('workout_name', row.get('workout_title', 'Workout'))
                    # If it looks like a filename, use type instead
                    if '.fit' in name.lower() or len(name) > 50:
                        name = row.get('type', 'Workout')
                    return name
                
                workout1_options = workouts_df['workout_day'].astype(str) + ' - ' + workouts_df.apply(format_workout_name, axis=1).str[:40]
                workout1_idx = st.selectbox(
                    "Select first workout:",
                    options=range(len(workout1_options)),
                    format_func=lambda x: workout1_options.iloc[x],
                    key="workout1"
                )
            
            with col2:
                st.markdown("**Workout 2** (Comparison)")
                workout2_options = workouts_df['workout_day'].astype(str) + ' - ' + workouts_df.apply(format_workout_name, axis=1).str[:40]
                workout2_idx = st.selectbox(
                    "Select second workout:",
                    options=range(len(workout2_options)),
                    format_func=lambda x: workout2_options.iloc[x],
                    key="workout2"
                )
            
            if st.button("⚖️ Compare Workouts", type="primary"):
                if workout1_idx == workout2_idx:
                    st.warning("Please select two different workouts to compare.")
                else:
                    workout1 = cycling_workouts[workout1_idx]
                    workout2 = cycling_workouts[workout2_idx]
                    
                    # Initialize comparator
                    comparator = WorkoutComparator()
                    
                    # Calculate similarity
                    similarity = comparator.calculate_similarity_score(workout1, workout2)
                    
                    st.info(f"**Similarity Score:** {similarity:.0f}%")
                    
                    # Perform detailed comparison
                    with st.spinner("Analyzing workouts..."):
                        comparison = comparator.compare_workouts_detailed(workout1, workout2)
                    
                    # Display the comparison
                    display_session_comparison(workout1, workout2, comparison)
    
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the API. Please ensure the FastAPI server is running.")
        st.code("python3 -m uvicorn src.api.app:app --reload", language="bash")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        import traceback
        with st.expander("Show Error Details"):
            st.code(traceback.format_exc())

def reset_form_state():
    st.session_state.show_notes_form = False
    st.session_state.notes_saved = False

# Apply custom styling
apply_custom_styling()

# Enhanced main title
st.markdown("""
<div class="main-header">
    <h1>🦆 QuackTrack Pro</h1>
    <p style="margin: 0; opacity: 0.9; font-size: 1.1rem;">AI-Powered Fitness Intelligence • Track • Analyze • Optimize</p>
</div>
""", unsafe_allow_html=True)

# Enhanced sidebar
st.sidebar.markdown("### 🎯 Navigation")
page = st.sidebar.radio("Go to", [
    '📊 Dashboard', 
    '🏆 Performance Analytics',
    '🎯 Achievements & Goals',
    '📅 Workout Calendar', 
    '🤖 AI Coach',
    '📦 Workout Data Ingestion',  # NEW: Manual matching workflow
], index=0)

if page == '📅 Workout Calendar':
    display_workout_calendar()

elif page == '🏆 Performance Analytics':
    display_performance_analytics()

elif page == '🎯 Achievements & Goals':
    from src.ui.tabs.achievements import render_achievements_tab
    render_achievements_tab()

elif page == '🤖 AI Coach':
    display_ai_coach()

# Session Comparison moved to Historical Analysis tab - keeping function for potential future use
# elif page == '🔄 Session Comparison':
#     display_session_comparison_page()

elif page == '📊 Dashboard':
    create_section_header("Training Dashboard", "📊")
    
    # Enhanced sidebar with styling
    st.sidebar.markdown("### ⏰ Time Period")
    time_period = st.sidebar.radio("Select Time Period", 
                                  ["📅 Last 4 Weeks", "📅 Last 8 Weeks", "📅 Last 12 Weeks", "🎯 Custom"])
    
    today = datetime.now().date()
    if time_period == "📅 Last 4 Weeks":
        dashboard_end_date = today
        dashboard_start_date = dashboard_end_date - timedelta(days=28)
    elif time_period == "📅 Last 8 Weeks":
        dashboard_end_date = today
        dashboard_start_date = dashboard_end_date - timedelta(days=56)
    elif time_period == "📅 Last 12 Weeks":
        dashboard_end_date = today
        dashboard_start_date = dashboard_end_date - timedelta(days=84)
    else:  # Custom
        st.sidebar.markdown("#### 🗓️ Custom Date Range")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            dashboard_start_date = st.date_input("Start Date", today - timedelta(days=28))
        with col2:
            dashboard_end_date = st.date_input("End Date", today)

    # Normalize date widget returns to plain date objects
    dashboard_start_date = _normalize_date_widget(dashboard_start_date)
    dashboard_end_date = _normalize_date_widget(dashboard_end_date)

    # Ensure we have valid dates
    if dashboard_start_date is None or dashboard_end_date is None:
        st.warning("Please select valid start and end dates for the dashboard.")
        st.stop()

    # Cast to concrete date types for downstream comparisons
    dashboard_start_date = cast(date, dashboard_start_date)
    dashboard_end_date = cast(date, dashboard_end_date)
    
    # Fetch data for selected time period
    try:
        # Fetch workouts for the selected week
        workouts_response = requests.get(
            f"{API_URL}/workouts/week",
            params={
                "start_date": dashboard_start_date.isoformat(),
                "end_date": dashboard_end_date.isoformat()
            }
        )
        if workouts_response.status_code != 200:
            st.error(f"Error fetching workout data: {workouts_response.status_code}")
            workouts_df = pd.DataFrame()
        else:
            result = workouts_response.json()
            # The /workouts/week endpoint returns {completed_workouts: [...], proposed_workouts: [...]}
            workouts = result.get('completed_workouts', []) if isinstance(result, dict) else result
            if workouts:
                workouts_df = pd.DataFrame(workouts)
                # Convert dates to datetime
                workouts_df['workout_day'] = pd.to_datetime(workouts_df['workout_day'])
            else:
                workouts_df = pd.DataFrame()
        
        # Fetch weekly summaries
        summaries_response = requests.get(f"{API_URL}/summaries")
        if summaries_response.status_code != 200:
            st.error("Error fetching summary data")
            summaries_df = pd.DataFrame()
        else:
            summaries = summaries_response.json()
            if summaries:
                summaries_df = pd.DataFrame(summaries)
                # Convert dates to datetime
                summaries_df['start_date'] = pd.to_datetime(summaries_df['start_date'])
                summaries_df['end_date'] = pd.to_datetime(summaries_df['end_date'])
                # Filter by date range
                summaries_df = summaries_df[(summaries_df['end_date'].dt.date >= dashboard_start_date) & 
                                           (summaries_df['start_date'].dt.date <= dashboard_end_date)]
            else:
                summaries_df = pd.DataFrame()
                
        # Check if we have data
        has_workout_data = not workouts_df.empty
        has_summary_data = not summaries_df.empty
                
        if not has_workout_data and not has_summary_data:
            st.warning(f"No training data found for the period {dashboard_start_date} to {dashboard_end_date}")
            st.info("Try selecting a different time period or import workout data.")
            # Skip the rest of the dashboard code if no data is available
            
        # ================== TOP OVERVIEW SECTION ==================
        st.subheader("Key Training Metrics")
        
        # Prepare metrics for display
        if has_workout_data:
            # Extract metrics from workout data
            total_workouts = len(workouts_df)
            
            # Normalize workout types to lowercase for consistent counting
            if 'type' in workouts_df.columns:
                workouts_df['type_lower'] = workouts_df['type'].str.lower()
                workout_types = workouts_df['type_lower'].value_counts().to_dict()
            else:
                workout_types = {}
            
            # Calculate TSS and duration metrics
            total_tss = 0
            total_duration = 0
            
            # Check if metrics column exists and contains the expected data
            if 'metrics' in workouts_df.columns:
                for metrics in workouts_df['metrics']:
                    if isinstance(metrics, dict):
                        total_tss += metrics.get('actual_tss', 0) or 0
                        total_duration += metrics.get('actual_duration', 0) or 0
            
            # Calculate averages
            avg_tss_per_workout = total_tss / total_workouts if total_workouts > 0 else 0
            training_hours = total_duration / 60  # Convert minutes to hours
            
            # Count workout types (now using lowercase)
            bike_workouts = workout_types.get('bike', 0)
            strength_workouts = workout_types.get('strength', 0)
            run_workouts = workout_types.get('run', 0)
            other_workouts = total_workouts - (bike_workouts + strength_workouts + run_workouts)
            
            # Additional metrics from summary data
            avg_sleep_quality = None
            avg_energy = None
            
            if has_summary_data and 'avg_sleep_quality' in summaries_df.columns and 'avg_daily_energy' in summaries_df.columns:
                avg_sleep_quality = summaries_df['avg_sleep_quality'].mean()
                avg_energy = summaries_df['avg_daily_energy'].mean()
            
            # Display key metrics with enhanced styling
            create_section_header("Training Overview", "📊")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                create_custom_metric("Training Sessions", str(total_workouts), "🏃‍♂️", "blue")
                create_custom_metric("Training Hours", f"{training_hours:.1f}", "⏱️", "green")
            
            with col2:
                create_custom_metric("Total TSS", f"{total_tss:.0f}", "🎯", "purple")
                create_custom_metric("Avg TSS/Workout", f"{avg_tss_per_workout:.0f}", "📊", "orange")
            
            with col3:
                if avg_sleep_quality is not None:
                    create_custom_metric("Sleep Quality", f"{avg_sleep_quality:.1f}/5", "😴", "blue")
                else:
                    create_custom_metric("Bike Workouts", str(bike_workouts), "🚴‍♂️", "blue")
                    
                if avg_energy is not None:
                    create_custom_metric("Energy Level", f"{avg_energy:.1f}/5", "⚡", "orange")
                else:
                    create_custom_metric("Strength Workouts", str(strength_workouts), "💪", "purple")
            
            # ================== TRENDS SECTION ==================
            create_section_header("Training Trends", "📈")
            
            trend_tabs = st.tabs(["📊 TSS & Intensity", "⚖️ Workout Balance", "😴 Sleep & Recovery"])
            
            with trend_tabs[0]:  # TSS & Intensity Tab
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    # Weekly TSS Chart
                    if has_summary_data and 'total_tss' in summaries_df.columns:
                        # Create a formatted date label for each week
                        summaries_df['week_label'] = summaries_df['start_date'].dt.strftime('%b %d')
                        
                        # Detect and remove duplicate weeks
                        # Keep the entry with the most complete data (highest ID) for each week
                        weekly_tss_df = summaries_df.sort_values(['week_label', 'id'], ascending=[True, False])
                        weekly_tss_df = weekly_tss_df.drop_duplicates(subset=['week_label'], keep='first')
                        
                        # Sort by date for display
                        weekly_tss_df = weekly_tss_df.sort_values('start_date')
                        
                        # Debug message
                        st.caption(f"Showing data for {len(weekly_tss_df)} unique weeks")
                        
                        # Plot weekly TSS trend
                        fig = px.bar(
                            weekly_tss_df,
                            x='week_label',
                            y='total_tss',
                            title="Weekly TSS Trend",
                            labels={"week_label": "Week Starting", "total_tss": "Training Stress Score"},
                            color_discrete_sequence=['#4CAF50'],
                        )
                        fig.update_layout(xaxis={'categoryorder':'array', 'categoryarray':weekly_tss_df['week_label']})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Not enough weekly summary data to display TSS trend")
                
                with col2:
                    if has_workout_data:
                        # Get data to calculate intensity distribution
                        intensity_data = []
                        labels = []
                        
                        # For bike workouts, get power zones (case insensitive)
                        bike_workouts_df = workouts_df[workouts_df['type'].str.lower() == 'bike'] if 'type' in workouts_df.columns else pd.DataFrame()
                        
                        if not bike_workouts_df.empty:
                            # Debug info
                            st.caption(f"Found {len(bike_workouts_df)} bike workouts")
                            
                            # Create a mapping for zone names 
                            zone_name_mapping = {
                                'zone1': 'Zone 1 (Recovery)', 
                                'zone2': 'Zone 2 (Endurance)', 
                                'zone3': 'Zone 3 (Tempo)', 
                                'zone4': 'Zone 4 (Threshold)', 
                                'zone5': 'Zone 5 (VO2 Max)',
                                'Zone 1 (Recovery)': 'Zone 1 (Recovery)',
                                'Zone 2 (Endurance)': 'Zone 2 (Endurance)',
                                'Zone 3 (Tempo)': 'Zone 3 (Tempo)',
                                'Zone 4 (Threshold)': 'Zone 4 (Threshold)',
                                'Zone 5 (VO2 Max)': 'Zone 5 (VO2 Max)'
                            }
                            
                            zone_minutes = {
                                'Zone 1 (Recovery)': 0, 
                                'Zone 2 (Endurance)': 0, 
                                'Zone 3 (Tempo)': 0, 
                                'Zone 4 (Threshold)': 0, 
                                'Zone 5 (VO2 Max)': 0
                            }
                            
                            # Aggregate zone data across all workouts
                            for _, workout in bike_workouts_df.iterrows():
                                if isinstance(workout.get('power_data'), dict) and 'zones' in workout['power_data']:
                                    power_zones = workout['power_data']['zones']
                                    if isinstance(power_zones, dict):
                                        for zone, percentage in power_zones.items():
                                            if percentage is not None and percentage > 0:
                                                # Map zone name to standard format
                                                standard_zone = zone_name_mapping.get(zone)
                                                if standard_zone in zone_minutes:
                                                    zone_minutes[standard_zone] += percentage
                            
                            # Calculate averages
                            num_workouts = len(bike_workouts_df)
                            if num_workouts > 0:
                                for zone, total in zone_minutes.items():
                                    avg_percentage = total / num_workouts
                                    if avg_percentage > 0:  # Only add non-zero values
                                        intensity_data.append(avg_percentage)
                                        labels.append(zone)
                            
                            # Create and display the chart
                            if intensity_data:
                                fig = px.pie(
                                    values=intensity_data,
                                    names=labels,
                                    title="Power Zone Distribution",
                                    hole=0.4,
                                    color_discrete_sequence=px.colors.sequential.Viridis
                                )
                                fig.update_traces(textposition='inside', textinfo='percent+label')
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("No power zone data available")
                        else:
                            st.info("No bike workout data with power metrics available")
            
            with trend_tabs[1]:  # Workout Balance Tab
                col1, col2 = st.columns(2)
                
                with col1:
                    # Workout type distribution
                    if has_workout_data and 'type' in workouts_df.columns:
                        workout_counts = workouts_df['type'].value_counts().reset_index()
                        workout_counts.columns = ['Type', 'Count']
                        
                        # Create pie chart
                        fig = px.pie(
                            workout_counts, 
                            values='Count', 
                            names='Type',
                            title="Workout Type Distribution",
                            color_discrete_sequence=px.colors.qualitative.Bold
                        )
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No workout type data available")
                
                with col2:
                    # Weekly workout count
                    if has_workout_data and 'workout_day' in workouts_df.columns:
                        # Group by week and count workouts
                        workouts_df['week'] = workouts_df['workout_day'].dt.isocalendar().week
                        workouts_df['year'] = workouts_df['workout_day'].dt.isocalendar().year
                        workouts_df['week_label'] = workouts_df['workout_day'].dt.strftime('%b %d')
                        
                        # Count by week and workout type
                        workout_counts = workouts_df.groupby(['year', 'week', 'week_label', 'type']).size().reset_index(name='count')
                        
                        # Pivot the data for stacked bar chart
                        pivot_df = workout_counts.pivot_table(
                            index=['year', 'week', 'week_label'], 
                            columns='type', 
                            values='count',
                            fill_value=0
                        ).reset_index()
                        
                        # Sort by year and week
                        pivot_df = pivot_df.sort_values(['year', 'week'])
                        
                        # Plot stacked bar chart
                        fig = px.bar(
                            pivot_df, 
                            x='week_label',
                            y=pivot_df.columns[3:],  # Skip year, week, week_label columns
                            title="Weekly Workout Count by Type",
                            labels={'value': 'Number of Workouts', 'week_label': 'Week'},
                            color_discrete_sequence=px.colors.qualitative.Bold
                        )
                        fig.update_layout(legend_title="Workout Type")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No workout date data available")
            
            with trend_tabs[2]:  # Sleep & Recovery Tab
                col1, col2 = st.columns(2)
                
                with col1:
                    # Sleep quality trend
                    if has_summary_data and 'avg_sleep_quality' in summaries_df.columns:
                        # Create a formatted date label for each week if not already done
                        if 'week_label' not in summaries_df.columns:
                            summaries_df['week_label'] = summaries_df['start_date'].dt.strftime('%b %d')
                        
                        # Deduplicate weeks using the same approach as for TSS
                        sleep_df = summaries_df.sort_values(['week_label', 'id'], ascending=[True, False])
                        sleep_df = sleep_df.drop_duplicates(subset=['week_label'], keep='first')
                        sleep_df = sleep_df.sort_values('start_date')
                        
                        fig = px.line(
                            sleep_df,
                            x='week_label',
                            y='avg_sleep_quality',
                            title="Sleep Quality Trend",
                            labels={'week_label': 'Week', 'avg_sleep_quality': 'Sleep Quality (1-5)'},
                            markers=True,
                            color_discrete_sequence=['#9C27B0']
                        )
                        fig.update_layout(
                            yaxis=dict(range=[1, 5]),
                            xaxis={'categoryorder':'array', 'categoryarray':sleep_df['week_label']}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No sleep quality data available")
                
                with col2:
                    # Energy level trend
                    if has_summary_data and 'avg_daily_energy' in summaries_df.columns:
                        # Create a formatted date label for each week if not already done
                        if 'week_label' not in summaries_df.columns:
                            summaries_df['week_label'] = summaries_df['start_date'].dt.strftime('%b %d')
                        
                        # Deduplicate weeks using the same approach as for TSS
                        energy_df = summaries_df.sort_values(['week_label', 'id'], ascending=[True, False])
                        energy_df = energy_df.drop_duplicates(subset=['week_label'], keep='first')
                        energy_df = energy_df.sort_values('start_date')
                        
                        fig = px.line(
                            energy_df,
                            x='week_label',
                            y='avg_daily_energy',
                            title="Energy Level Trend",
                            labels={'week_label': 'Week', 'avg_daily_energy': 'Energy Level (1-5)'},
                            markers=True,
                            color_discrete_sequence=['#FF9800']
                        )
                        fig.update_layout(
                            yaxis=dict(range=[1, 5]),
                            xaxis={'categoryorder':'array', 'categoryarray':energy_df['week_label']}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No energy level data available")
                
                # Recovery analysis
                if has_summary_data and 'muscle_soreness_patterns' in summaries_df.columns and 'general_fatigue_level' in summaries_df.columns:
                    # Get the most recent summary with recovery data
                    recent_summary = summaries_df.sort_values('end_date', ascending=False).iloc[0]
                    
                    if pd.notna(recent_summary.get('muscle_soreness_patterns')) or pd.notna(recent_summary.get('general_fatigue_level')):
                        st.subheader("Recent Recovery Analysis")
                        
                        recovery_cols = st.columns(2)
                        with recovery_cols[0]:
                            st.markdown("##### Muscle Soreness")
                            if pd.notna(recent_summary.get('muscle_soreness_patterns')):
                                st.text(recent_summary['muscle_soreness_patterns'])
                            else:
                                st.info("No recent muscle soreness data")
                        
                        with recovery_cols[1]:
                            st.markdown("##### Fatigue Level")
                            if pd.notna(recent_summary.get('general_fatigue_level')):
                                st.text(recent_summary['general_fatigue_level'])
                            else:
                                st.info("No recent fatigue data")
            
            # ================== WORKOUT ANALYSIS SECTION ==================
            st.subheader("Recent Workout Analysis")
            
            if has_workout_data:
                # Get the most recent 5 workouts
                recent_workouts = workouts_df.sort_values('workout_day', ascending=False).head(5)
                
                for i, (_, workout) in enumerate(recent_workouts.iterrows()):
                    # Use workout_name if available (from proposed workout matching), otherwise fall back to title
                    display_name = workout.get('workout_name', workout.get('title', 'Workout'))
                    # If it still looks like a filename (has .fit or similar), use just "Workout"
                    if '.fit' in display_name.lower() or len(display_name) > 50:
                        display_name = workout.get('type', 'Workout')
                    
                    with st.expander(f"{workout['workout_day'].strftime('%Y-%m-%d')} - {display_name}", expanded=i==0):
                        workout_cols = st.columns(2)
                        
                        with workout_cols[0]:
                            # Basic workout info
                            st.markdown(f"**Type:** {workout.get('type', 'Unknown')}")
                            
                            # Show metrics if available
                            if isinstance(workout.get('metrics'), dict):
                                metrics = workout['metrics']
                                st.markdown("##### Metrics")
                                metrics_str = ""
                                if metrics.get('actual_tss'):
                                    metrics_str += f"- TSS: {metrics['actual_tss']:.1f}\n"
                                if metrics.get('actual_duration'):
                                    metrics_str += f"- Duration: {metrics['actual_duration']:.1f} min\n"
                                if metrics.get('rpe'):
                                    metrics_str += f"- RPE: {metrics['rpe']}\n"
                                
                                st.markdown(metrics_str)
                            
                            # Show power data if available
                            if isinstance(workout.get('power_data'), dict):
                                power_data = workout['power_data']
                                st.markdown("##### Power Data")
                                power_str = ""
                                if power_data.get('average'):
                                    power_str += f"- Avg Power: {power_data['average']:.0f}W\n"
                                if power_data.get('normalized_power'):
                                    power_str += f"- NP: {power_data['normalized_power']:.0f}W\n"
                                if power_data.get('intensity_factor'):
                                    power_str += f"- IF: {power_data['intensity_factor']:.2f}\n"
                                
                                st.markdown(power_str)
                        
                        with workout_cols[1]:
                            # Show heart rate data if available
                            if isinstance(workout.get('heart_rate_data'), dict):
                                hr_data = workout['heart_rate_data']
                                st.markdown("##### Heart Rate Data")
                                hr_str = ""
                                if hr_data.get('average'):
                                    hr_str += f"- Avg HR: {hr_data['average']:.0f} bpm\n"
                                if hr_data.get('max'):
                                    hr_str += f"- Max HR: {hr_data['max']:.0f} bpm\n"
                                
                                st.markdown(hr_str)
                            
                            # Show athlete comments if available
                            if pd.notna(workout.get('athlete_comments')):
                                st.markdown("##### Comments")
                                st.markdown(f"_{workout['athlete_comments']}_")
                        
                        # Show zones visualization if available for power or heart rate
                        zones_cols = st.columns(2)
                        
                        with zones_cols[0]:
                            # Power zones
                            if isinstance(workout.get('power_data'), dict) and isinstance(workout['power_data'].get('zones'), dict):
                                zones = workout['power_data']['zones']
                                if zones:
                                    # Filter out zero values
                                    zones = {k: v for k, v in zones.items() if v > 0}
                                    
                                    if zones:
                                        fig = px.bar(
                                            x=list(zones.keys()),
                                            y=list(zones.values()),
                                            title="Power Zones",
                                            labels={'x': 'Zone', 'y': 'Time %'},
                                            color_discrete_sequence=['#4CAF50']
                                        )
                                        fig.update_layout(showlegend=False)
                                        st.plotly_chart(fig, use_container_width=True)
                        
                        with zones_cols[1]:
                            # Heart rate zones
                            if isinstance(workout.get('heart_rate_data'), dict) and isinstance(workout['heart_rate_data'].get('zones'), dict):
                                zones = workout['heart_rate_data']['zones']
                                if zones:
                                    # Filter out zero values
                                    zones = {k: v for k, v in zones.items() if v > 0}
                                    
                                    if zones:
                                        fig = px.bar(
                                            x=list(zones.keys()),
                                            y=list(zones.values()),
                                            title="Heart Rate Zones",
                                            labels={'x': 'Zone', 'y': 'Time %'},
                                            color_discrete_sequence=['#F44336']
                                        )
                                        fig.update_layout(showlegend=False)
                                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Show athlete comments if available
                        if pd.notna(workout.get('athlete_comments')):
                            st.markdown("##### Athlete Comments")
                            st.info(workout['athlete_comments'])
                
                # Link to detailed views
                st.markdown("---")
                st.markdown("Need more details? View full workout history in the [View Data](#view-data) section or check [Weekly Summaries](#weekly-summary).")
            else:
                st.info("No recent workout data available for analysis")
            
        else:
            st.warning("No workout data available for the selected time period")
            
    except Exception as e:
        st.error(f"Error loading dashboard data: {str(e)}")
        st.exception(e)

elif page == '� Workout Data Ingestion':
    create_section_header("Workout Data Ingestion", "📦")
    
    st.info("💡 **New Manual Matching Workflow**: Sync data from TrainingPeaks, then manually match workouts to ensure 100% accuracy before AI analysis.")
    
    # Import helper functions
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    from storage.workout_matching import (
        get_unmatched_workouts,
        get_proposed_workouts_for_week,
        match_workout_to_proposed,
        get_week_start_date
    )
    from utils.trainingpeaks_sync import TrainingPeaksSync
    from storage.database import WorkoutDatabase
    from utils.fit_file_analyzer import FitFileAnalyzer
    from utils.workout_visualizer import WorkoutVisualizer
    from utils.fit_parser import FitParser
    
    # ========== SECTION A: SYNC & MATCH NEW WORKOUTS ==========
    with st.expander("📥 Sync & Match New Workouts", expanded=True):
        st.markdown("### Step 1: Sync from TrainingPeaks")
        
        # Check for credentials
        load_dotenv()
        tp_username = os.getenv("TRAININGPEAKS_USERNAME")
        tp_password = os.getenv("TRAININGPEAKS_PASSWORD")
        
        if not tp_username or not tp_password:
            st.warning("⚠️ TrainingPeaks credentials not configured!")
            st.markdown("""
            **Setup Instructions:**
            1. Create a `.env` file in your project root
            2. Add your credentials:
            ```
            TRAININGPEAKS_USERNAME=your_username
            TRAININGPEAKS_PASSWORD=your_password
            ```
            3. Reload this page
            """)
        else:
            st.success(f"✅ Logged in as: {tp_username}")
            
            # Date range selection (defaults to current week)
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                today = datetime.now().date()
                days_since_monday = today.weekday()
                this_monday = today - timedelta(days=days_since_monday)
                
                sync_start_date = st.date_input(
                    "Start Date",
                    value=this_monday,
                    key="sync_start_date"
                )
            
            with col2:
                this_sunday = this_monday + timedelta(days=6)
                sync_end_date = st.date_input(
                    "End Date",
                    value=this_sunday,
                    key="sync_end_date"
                )
            
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                sync_button = st.button("🚀 Sync Data", type="primary", use_container_width=True)
            
            if isinstance(sync_start_date, date) and isinstance(sync_end_date, date):
                st.info(f"📊 Will sync from **{sync_start_date.strftime('%a, %b %d')}** to **{sync_end_date.strftime('%a, %b %d')}**")
            
            # Handle sync button click
            if sync_button:
                if not isinstance(sync_start_date, date) or not isinstance(sync_end_date, date):
                    st.error("Please select valid start and end dates")
                else:
                    st.markdown("---")
                    st.info("🔐 **Note:** You may need to solve a captcha if one appears in the browser")
                    
                    try:
                        with st.spinner("🌐 Syncing data from TrainingPeaks..."):
                            sync = TrainingPeaksSync()
                            results = sync.run_sync(sync_start_date, sync_end_date)
                        
                        if results:
                            st.success(f"""
                            ✅ **Sync Complete!**
                            
                            - FIT Files Uploaded: **{results['fit_files']}**
                            - Workouts CSV: **{'✅ Success' if results['workouts'] else '❌ Failed'}**
                            - Metrics CSV: **{'✅ Success' if results['metrics'] else '❌ Failed'}**
                            """)
                            
                            if results['errors']:
                                st.warning(f"⚠️ {len(results['errors'])} errors occurred:")
                                for error in results['errors']:
                                    st.text(f"  • {error}")
                            
                            # Set flag to load matching interface
                            st.session_state.sync_completed = True
                            st.session_state.sync_date_range = (sync_start_date, sync_end_date)
                            st.rerun()
                        else:
                            st.error("❌ Sync failed. Check the console output for details.")
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        with st.expander("Show error details"):
                            st.code(traceback.format_exc())
        
        # Step 2: Match workouts (only show if sync completed)
        if st.session_state.get('sync_completed', False):
            st.markdown("---")
            st.markdown("### Step 2: Match Workouts")
            
            # Get date range from session state
            date_range = st.session_state.get('sync_date_range')
            if date_range:
                start_date, end_date = date_range
                
                # Get unmatched workouts
                db_path = os.path.join(parent_dir, 'data', 'fitness_data.db')
                unmatched = get_unmatched_workouts(db_path, start_date.isoformat(), end_date.isoformat())
                
                if not unmatched:
                    st.success("🎉 All workouts in this date range are already matched!")
                    if st.button("Start New Sync"):
                        st.session_state.sync_completed = False
                        st.rerun()
                else:
                    st.info(f"📋 Found **{len(unmatched)}** unmatched workouts")
                    
                    # Initialize current workout index
                    if 'current_workout_idx' not in st.session_state:
                        st.session_state.current_workout_idx = 0
                    
                    # Get current workout
                    idx = st.session_state.current_workout_idx
                    if idx < len(unmatched):
                        workout = unmatched[idx]
                        
                        # Progress indicator
                        st.progress((idx + 1) / len(unmatched), text=f"Workout {idx + 1} of {len(unmatched)}")
                        
                        # Display workout details
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.markdown("#### 📊 Workout Details")
                            st.markdown(f"**Date:** {workout['workout_date']} (PST)")
                            st.markdown(f"**Title:** {workout['title']}")
                            if workout['tss']:
                                st.markdown(f"**TSS:** {workout['tss']}")
                            if workout['duration_minutes']:
                                st.markdown(f"**Duration:** {workout['duration_minutes']:.0f} min")
                            if workout['intensity_factor']:
                                st.markdown(f"**IF:** {workout['intensity_factor']:.2f}")
                            if workout['comments']:
                                st.markdown(f"**Comments:** {workout['comments']}")
                            if workout['fit_filename']:
                                st.markdown(f"**FIT File:** {workout['fit_filename']}")
                            
                            # Display power/HR chart if FIT file exists
                            if workout['fit_file_id']:
                                try:
                                    db = WorkoutDatabase(db_path)
                                    fit_file_data = db.get_fit_file_by_id(workout['fit_file_id'])
                                    
                                    if fit_file_data and fit_file_data['file_content']:
                                        with st.spinner("Loading workout chart..."):
                                            # Parse FIT file
                                            parser = FitParser()
                                            parsed_data = parser.parse_fit_file(fit_file_data['file_content'])
                                            
                                            if parsed_data and parsed_data.get('records'):
                                                # Create simple power/HR chart
                                                visualizer = WorkoutVisualizer()
                                                
                                                # Get peak efforts for the chart
                                                from utils.fit_file_analyzer import FitFileAnalyzer
                                                temp_analyzer = FitFileAnalyzer()
                                                peak_efforts = temp_analyzer._calculate_peak_efforts(parsed_data)
                                                
                                                # Create dashboard
                                                fig = visualizer.create_workout_dashboard(parsed_data, peak_efforts)
                                                st.plotly_chart(fig, use_container_width=True, key=f"chart_{workout['id']}")
                                            else:
                                                st.info("📊 Chart unavailable (no data records)")
                                except Exception as chart_error:
                                    st.info(f"📊 Chart unavailable: {str(chart_error)[:50]}")
                            else:
                                st.info("📊 No FIT file linked - chart unavailable")
                        
                        with col2:
                            st.markdown("#### 🎯 Match to Proposed Workout")
                            
                            # Get proposed workouts for the week
                            workout_date = datetime.strptime(workout['workout_date'], '%Y-%m-%d %H:%M:%S').date()
                            week_start = get_week_start_date(workout_date.isoformat())
                            proposed_workouts = get_proposed_workouts_for_week(db_path, week_start)
                            
                            # Create dropdown options
                            options = []
                            for pw in proposed_workouts:
                                label = f"{pw['workout_day']} - {pw['name']}"
                                if pw['tss']:
                                    label += f" (TSS: {pw['tss']})"
                                options.append((label, pw['name']))
                            
                            # Add "Other (Custom)" option
                            options.append(("Other (Custom workout/warm-up/cool-down)", "OTHER"))
                            
                            # Dropdown
                            selected_option = st.selectbox(
                                "Select proposed workout:",
                                options=[opt[0] for opt in options],
                                key=f"workout_select_{workout['id']}"
                            )
                            
                            # Get the actual name from the selected option
                            selected_name = next((opt[1] for opt in options if opt[0] == selected_option), None)
                            
                            # If "Other" selected, show text input
                            if selected_name == "OTHER":
                                custom_name = st.text_input(
                                    "Enter workout name:",
                                    placeholder="e.g., Warm-up, Cool-down, Hike",
                                    key=f"custom_name_{workout['id']}"
                                )
                                if custom_name:
                                    selected_name = custom_name
                                else:
                                    selected_name = None
                            
                            # Match & Analyze button
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("✅ Match & Analyze", type="primary", use_container_width=True, disabled=(selected_name is None)):
                                    if selected_name:
                                        with st.spinner("Matching and analyzing..."):
                                            try:
                                                # Step 1: Save match to database
                                                match_workout_to_proposed(
                                                    db_path,
                                                    workout['id'],
                                                    selected_name,
                                                    'manual'
                                                )
                                                st.success(f"✅ Matched to: {selected_name}")
                                                
                                                # Step 2: Run AI analysis if FIT file exists
                                                if workout['fit_file_id']:
                                                    with st.spinner("🤖 Running AI analysis..."):
                                                        try:
                                                            # Get FIT file content from database
                                                            db = WorkoutDatabase(db_path)
                                                            fit_file_data = db.get_fit_file_by_id(workout['fit_file_id'])
                                                            
                                                            if fit_file_data and fit_file_data['file_content']:
                                                                # Get athlete FTP
                                                                settings = db.get_athlete_settings()
                                                                ftp = settings.get('ftp', 300)
                                                                
                                                                # Run analysis
                                                                analyzer = FitFileAnalyzer(use_dynamic_models=True)
                                                                analysis = analyzer.analyze_workout(
                                                                    fit_file_content=fit_file_data['file_content'],
                                                                    athlete_ftp=float(ftp),
                                                                    proposed_workout_name=selected_name
                                                                )
                                                                
                                                                if analysis:
                                                                    # Get AI analysis text
                                                                    ai_analysis = analysis.get('ai_analysis', '')
                                                                    
                                                                    # Store analysis in database
                                                                    analysis_id = db.store_workout_analysis(
                                                                        workout_id=workout['id'],
                                                                        fit_file_id=workout['fit_file_id'],
                                                                        analysis_text=ai_analysis,
                                                                        model_used=analysis.get('model_used', 'gemini-2.0-flash-exp')
                                                                    )
                                                                    
                                                                    # Store personal bests
                                                                    peak_efforts = analysis.get('peak_efforts', {})
                                                                    workout_date = workout['workout_date'][:10]
                                                                    pb_count = 0
                                                                    
                                                                    for effort_name, effort_data in peak_efforts.items():
                                                                        if isinstance(effort_data, dict) and 'power' in effort_data:
                                                                            pb_id = db.store_personal_best(
                                                                                effort_type=effort_name,
                                                                                effort_value=effort_data['power'],
                                                                                achieved_date=workout_date,
                                                                                athlete_id='default'
                                                                            )
                                                                            if pb_id:
                                                                                pb_count += 1
                                                                    
                                                                    st.success(f"✅ AI analysis complete! (ID: {analysis_id})")
                                                                    if pb_count > 0:
                                                                        st.success(f"🏆 {pb_count} personal best(s) recorded!")
                                                                else:
                                                                    st.warning("⚠️ Analysis returned no results")
                                                            else:
                                                                st.warning("⚠️ No FIT file content available for analysis")
                                                        
                                                        except Exception as analysis_error:
                                                            st.warning(f"⚠️ Could not analyze workout: {str(analysis_error)}")
                                                            # Continue anyway - matching is saved
                                                else:
                                                    st.info("ℹ️ No FIT file linked - skipping analysis")
                                                
                                                # Move to next workout
                                                st.session_state.current_workout_idx += 1
                                                if st.session_state.current_workout_idx >= len(unmatched):
                                                    st.balloons()
                                                    st.success("🎉 All workouts matched!")
                                                    st.session_state.sync_completed = False
                                                    st.session_state.current_workout_idx = 0
                                                
                                                st.rerun()
                                            
                                            except Exception as e:
                                                st.error(f"Error: {str(e)}")
                                                import traceback
                                                with st.expander("Show error details"):
                                                    st.code(traceback.format_exc())
                            
                            with col_btn2:
                                if st.button("⏭️ Skip", use_container_width=True):
                                    st.session_state.current_workout_idx += 1
                                    if st.session_state.current_workout_idx >= len(unmatched):
                                        st.info("End of workout list")
                                        st.session_state.sync_completed = False
                                        st.session_state.current_workout_idx = 0
                                    st.rerun()
    
    # ========== SECTION B: RE-MATCH EXISTING WORKOUTS ==========
    with st.expander("🔄 Re-match Existing Workouts", expanded=False):
        st.markdown("### Re-match Previously Matched Workouts")
        st.warning("🚧 Coming soon - Ability to change matches and re-analyze")
    
    # ========== SECTION C: MANAGE WORKOUTS (DANGER ZONE) ==========
    with st.expander("⚠️ Manage Workouts (Danger Zone)", expanded=False):
        st.markdown("### Delete Workouts")
        st.warning("🚧 Coming soon - Delete junk workouts and their analyses")


# REMOVED: Old tabs (Import Data, View Data, Proposed Workouts, Weekly Summary)
# These have been replaced by the new Workout Data Ingestion tab above

# ================== FOOTER ==================
st.markdown("---")
st.markdown("""
<div style="
    background: linear-gradient(45deg, #56ab2f 0%, #a8e063 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    text-align: center;
    margin-top: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
">
    <h4 style="margin: 0; color: white;">🦆 QuackTrack Pro</h4>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
        AI-Powered Fitness Tracking • Smart Training for the Digital Athlete
    </p>
    <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; opacity: 0.8;">
        Made with 🤖 and Streamlit
    </p>
</div>
""", unsafe_allow_html=True)