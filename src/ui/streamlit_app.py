# src/ui/streamlit_app.py
import sys
sys.path.append(".")

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import requests
import json
import plotly.express as px
from src.utils.proposed_workouts_processor import process_proposed_workouts

def display_weekly_summary(summary):
    """Display weekly summary data with error handling"""
    # Display summary metrics
    st.subheader("Weekly Totals")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total TSS", f"{summary.get('total_tss', 0):.1f}")
    with col2:
        st.metric("Training Hours", f"{summary.get('total_training_hours', 0):.1f}")
    with col3:
        st.metric("Sessions", summary.get('sessions_completed', 0))
    
    # Workout Types
    workout_types = summary.get('workout_types', [])
    if workout_types:
        st.subheader("Workout Types")
        st.write(", ".join(workout_types))
    
    # Qualitative Feedback
    st.subheader("Daily Notes")
    qualitative_feedback = summary.get('qualitative_feedback', [])
    if qualitative_feedback:
        for note in qualitative_feedback:
            with st.expander(f"{note.get('day', 'Unknown Day')} - {note.get('type', 'Unknown Type')}"):
                feedback = note.get('feedback', {})
                if feedback.get('how_it_felt'):
                    st.write("**How it felt:**", feedback['how_it_felt'])
                if feedback.get('technical_issues'):
                    st.write("**Technical issues:**", feedback['technical_issues'])
                if feedback.get('modifications'):
                    st.write("**Modifications:**", feedback['modifications'])
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
                zones_df = pd.DataFrame(
                    [(k, v) for k, v in metrics['zones'].items() if v is not None and v > 0],
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
                zones_df = pd.DataFrame(
                    [(k, v) for k, v in metrics['zones'].items() if v is not None and v > 0],
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
                    # Filter out None values and zeros
                    valid_zones = {k: v for k, v in zones.items() 
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
                    # Filter out None values and zeros
                    valid_zones = {k: v for k, v in zones.items() 
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

def display_workout_calendar():
    st.header("Workout Calendar")
    
    # Get current week number and date
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
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
        test_response = requests.get("http://localhost:8000/")
        if test_response.status_code != 200:
            st.error("Cannot connect to API server. Please ensure it's running.")
            return
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server. Please ensure it's running at http://localhost:8000/")
        return
    
    # Fetch proposed workouts for the selected week
    try:
        response = requests.get(
            "http://localhost:8000/proposed_workouts/week",
            params={
                "start_date": selected_week_start.strftime('%Y-%m-%d'),
                "end_date": selected_week_end.strftime('%Y-%m-%d')
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
                except:
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
        
        # Create the workout timer just once in the sidebar, outside of day tabs
        # This ensures it's always visible regardless of which tab is active
        create_workout_timer()
        
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
                                "http://localhost:8000/workout/performance",
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
                            st.markdown(f"### Workout Details")
                            display_bike_workout(workout)
                        elif workout_type in ["strength", "yoga", "other"]:
                            st.markdown(f"### Workout Details")
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
    """Display bike workout intervals"""
    st.subheader("Interval Structure")
    
    # Parse intervals from JSON string if needed
    intervals = workout.get('intervals')
    if isinstance(intervals, str):
        try:
            intervals = json.loads(intervals)
        except:
            st.warning("Could not parse intervals data")
            return
    
    if not intervals:
        st.info("No interval data available")
        return
    
    # Display intervals as a table
    intervals_data = []
    for i, interval in enumerate(intervals):
        interval_data = {
            "Name": interval.get('name', f"Interval {i+1}"),
            "Duration": f"{interval.get('duration', 0)/60:.1f} min" if interval.get('duration') else 'N/A',
        }
        
        # Handle different power target formats
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
            elif power_target.get('type') == 'range':
                min_val = power_target.get('min', 0)
                max_val = power_target.get('max', 0)
                unit = power_target.get('unit', 'watts')
                interval_data["Power"] = f"{min_val}-{max_val} {unit}"
            else:
                interval_data["Power"] = "Custom"
        
        # Add cadence info
        cadence = interval.get('cadenceTarget', {})
        if cadence:
            interval_data["Cadence"] = f"{cadence.get('min', 0)}-{cadence.get('max', 0)} rpm"
        
        intervals_data.append(interval_data)
    
    # Create DataFrame and display as table
    if intervals_data:
        intervals_df = pd.DataFrame(intervals_data)
        st.table(intervals_df)

def display_strength_workout_with_tracking(workout, unique_key=""):
    """Display strength workout with integrated tracking for each exercise"""
    st.subheader("Workout Routine")
    
    # Create a form for tracking data with a unique key
    with st.form(key=f"workout_tracking_{unique_key}_{workout.get('id')}"):
        # Parse sections from JSON string if needed
        sections = workout.get('sections')
        if isinstance(sections, str):
            try:
                sections = json.loads(sections)
            except Exception as e:
                st.warning(f"Could not parse workout sections data: {str(e)}")
                return
        
        if not sections:
            st.info("No section data available")
            return
        
        # Store workout performance data
        all_exercise_data = {}
        
        # Process each section
        for section_idx, section in enumerate(sections):
            section_name = section.get('name', f"Section {section_idx+1}")
            
            # Section header with clear visual distinction
            st.markdown(f"### {section_name}")
            
            # Section info
            if section.get('duration'):
                st.write(f"**Duration:** {section.get('duration')/60:.1f} min")
            if section.get('rounds'):
                st.write(f"**Rounds:** {section.get('rounds')}")
            
            # Initialize section data
            section_exercises = {}
            
            # Process exercises in this section
            for ex_idx, exercise in enumerate(section.get('exercises', [])):
                ex_name = exercise.get('name', f"Exercise {ex_idx+1}")
                
                # Create a unique key for this exercise including the outer unique key
                ex_key = f"{unique_key}_s{section_idx}_e{ex_idx}"
                
                # Exercise header with strong visual distinction
                st.markdown(f"#### {ex_name}")
                
                # Display any cues/notes first
                if exercise.get('cues'):
                    cues = exercise.get('cues')
                    if isinstance(cues, list):
                        st.markdown("**Cues:**")
                        cue_text = ""
                        for cue in cues:
                            cue_text += f"- {cue}\n"
                        st.markdown(cue_text)
                    else:
                        st.markdown(f"**Cues:** {cues}")
                
                # Initialize exercise data structure
                exercise_data = {
                    "name": ex_name,
                    "sets": []
                }
                
                # Process sets with interleaved tracking
                sets = exercise.get('sets', [])
                if sets:
                    # Create columns for headers
                    cols = st.columns([1, 1, 2])
                    with cols[0]:
                        st.write("**Set Details**")
                    with cols[1]:
                        st.write("**Target**")
                    with cols[2]:
                        st.write("**Your Performance**")
                    
                    # For each set, display prescribed info and tracking fields side by side
                    for set_idx, set_info in enumerate(sets):
                        set_key = f"{ex_key}_set{set_idx}"
                        
                        # Format target information
                        target_desc = []
                        if set_info.get('reps'):
                            target_desc.append(f"Reps: {set_info.get('reps')}")
                        elif set_info.get('targetReps'):
                            target = set_info.get('targetReps', {})
                            if isinstance(target, dict):
                                target_reps = f"{target.get('min', 0)}-{target.get('max', 0)}"
                                target_desc.append(f"Reps: {target_reps}")
                        
                        if set_info.get('weight'):
                            weight = set_info.get('weight', {})
                            if isinstance(weight, dict):
                                target_weight = f"{weight.get('min', 0)}-{weight.get('max', 0)} {weight.get('unit', 'lbs')}"
                                target_desc.append(f"Weight: {target_weight}")
                            else:
                                target_desc.append(f"Weight: {weight} lbs")
                        
                        if set_info.get('workTime'):
                            target_desc.append(f"Work: {set_info.get('workTime')}s")
                        if set_info.get('restTime'):
                            target_desc.append(f"Rest: {set_info.get('restTime')}s")
                        if set_info.get('tempo'):
                            target_desc.append(f"Tempo: {set_info.get('tempo')}")
                            
                        target_text = "\n".join(target_desc)
                        
                        # Create a row with 3 columns for this set
                        cols = st.columns([1, 1, 2])
                        
                        # Column 1: Set number
                        with cols[0]:
                            st.write(f"**Set {set_idx+1}**")
                        
                        # Column 2: Target details
                        with cols[1]:
                            st.text(target_text)
                        
                        # Column 3: Input fields
                        with cols[2]:
                            # Create 3 sub-columns for reps, weight, notes
                            subcol1, subcol2, subcol3 = st.columns(3)
                            
                            with subcol1:
                                actual_reps = st.number_input("Reps", 0, 100, 0, key=f"reps_{set_key}")
                            
                            with subcol2:
                                actual_weight = st.number_input("Lbs", 0, 500, 0, step=5, key=f"weight_{set_key}")
                            
                            with subcol3:
                                notes = st.text_input("Notes", key=f"notes_{set_key}")
                        
                        # Store the set data
                        exercise_data["sets"].append({
                            "set_number": set_idx + 1,
                            "actual_reps": actual_reps,
                            "actual_weight": actual_weight,
                            "notes": notes
                        })
                
                # Add this exercise to the section using a consistent key without the unique prefix
                # (just for internal data organization)
                section_exercises[f"s{section_idx}_e{ex_idx}"] = exercise_data
            
            # Add this section's exercises to the overall data
            all_exercise_data[f"section_{section_idx}"] = {
                "name": section_name,
                "exercises": section_exercises
            }
        
        # General workout notes
        st.markdown("### Overall Workout Notes")
        general_notes = st.text_area("Notes", height=100, key=f"notes_{unique_key}")
        
        # Submit button
        submitted = st.form_submit_button("Save Workout Data")
        if submitted:
            # Prepare data for saving
            performance_data = {
                "sections": [
                    {
                        "name": section_data["name"],
                        "exercises": list(section_data["exercises"].values())
                    } for section_key, section_data in all_exercise_data.items()
                ],
                "general_notes": general_notes
            }
            
            try:
                with st.spinner("Saving workout data..."):
                    # Call the API to save the data
                    response = requests.post(
                        "http://localhost:8000/workout/performance",
                        data={
                            "workout_id": workout.get('id', 0),
                            "workout_date": workout.get('date', ''),
                            "actual_duration": workout.get('plannedDuration', 0),
                            "performance_data": json.dumps(performance_data)
                        }
                    )
                
                if response.status_code == 200:
                    st.success("✅ Workout data saved successfully!")
                else:
                    st.error(f"Error saving data: {response.text}")
                    
            except Exception as e:
                st.error(f"Error saving workout data: {str(e)}")

def create_workout_timer():
    """Create a persistent timer for workout tracking"""
    # Initialize timer state if not already in session state
    if 'timer_running' not in st.session_state:
        st.session_state.timer_running = False
        st.session_state.timer_duration = 60
        st.session_state.rest_duration = 30
        st.session_state.timer_mode = "Work"  # "Work" or "Rest"
        st.session_state.timer_end_time = None
        st.session_state.last_update = datetime.now()
    
    # Create a container that will always be visible and fixed at the top
    with st.sidebar:
        st.markdown("### 🕒 Workout Timer")
        st.markdown("*Timer stays visible while you scroll*")
        
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
        
        # Controls row
        col1, col2 = st.columns(2)
        with col1:
            if not st.session_state.timer_running:
                if st.button("▶️ Start", key="start_timer_button", use_container_width=True):
                    st.session_state.timer_running = True
                    st.session_state.timer_end_time = datetime.now() + timedelta(seconds=work_duration)
                    st.session_state.timer_mode = "Work"
                    st.session_state.last_update = datetime.now()
                    st.rerun()
            else:
                if st.button("⏹️ Stop", key="stop_timer_button", use_container_width=True):
                    st.session_state.timer_running = False
                    st.rerun()
        
        with col2:
            if st.button("🔄 Reset", key="reset_timer_button", use_container_width=True):
                st.session_state.timer_running = False
                st.session_state.timer_mode = "Work"
                st.rerun()
        
        # Current mode indicator with color coding
        mode_color = "#4CAF50" if st.session_state.timer_mode == "Work" else "#FF9800"
        st.markdown(f"""
            <div style='background-color: {mode_color}; padding: 10px; border-radius: 5px; text-align: center; color: white; font-weight: bold;'>
                {st.session_state.timer_mode} MODE
            </div>
        """, unsafe_allow_html=True)
            
        # Calculate and display time remaining if timer is running
        if st.session_state.timer_running and st.session_state.timer_end_time:
            now = datetime.now()
            time_remaining = max(0, (st.session_state.timer_end_time - now).total_seconds())
            
            # Check if timer has ended
            if time_remaining <= 0:
                # Switch modes
                if st.session_state.timer_mode == "Work":
                    st.session_state.timer_mode = "Rest"
                    st.session_state.timer_end_time = datetime.now() + timedelta(seconds=rest_duration)
                    # Show visual notification
                    st.warning("⏰ Work period complete! Switching to REST mode")
                else:
                    st.session_state.timer_mode = "Work"
                    st.session_state.timer_end_time = datetime.now() + timedelta(seconds=work_duration)
                    # Show visual notification
                    st.success("⏰ Rest period complete! Switching to WORK mode")
                
                # Calculate new time remaining
                time_remaining = st.session_state.rest_duration if st.session_state.timer_mode == "Rest" else st.session_state.timer_duration
                st.rerun()
            
            # Display progress bar and time
            current_duration = st.session_state.timer_duration if st.session_state.timer_mode == "Work" else st.session_state.rest_duration
            progress = 1.0 - (time_remaining / current_duration)
            
            # Only update UI if sufficient time has passed (to avoid excessive reruns)
            time_since_update = (now - st.session_state.last_update).total_seconds()
            if time_since_update >= 0.5:  # Update every half second
                st.session_state.last_update = now
                st.progress(progress)
                st.markdown(f"<h2 style='text-align: center;'>{int(time_remaining)}s</h2>", unsafe_allow_html=True)
                
                # Automatic rerun to update the timer if more than 1 second remains
                if st.session_state.timer_running and time_remaining > 1:
                    st.rerun()
        else:
            # Show empty progress bar when not running
            st.progress(0.0)
            if not st.session_state.timer_running:
                st.markdown("<p style='text-align: center; color: gray;'>Timer not running</p>", unsafe_allow_html=True)
    
    # Return the timer state for reference
    return st.session_state.timer_running

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

def reset_form_state():
    st.session_state.show_notes_form = False
    st.session_state.notes_saved = False

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ['Dashboard', 'Workout Calendar', 'Import Data', 'Weekly Summary', 'View Data', 'Proposed Workouts'])

# Main content
st.title("Fitness Tracker")

if page == 'Workout Calendar':
    display_workout_calendar()

elif page == 'Dashboard':
    st.header("Dashboard")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Workouts")
        try:
            response = requests.get("http://localhost:8000/workouts")
            workouts = response.json()
            if workouts:
                df = pd.DataFrame(workouts)
                st.dataframe(df)
            else:
                st.info("No workouts found")
        except:
            st.error("Could not connect to the API")
    
    with col2:
        st.subheader("Weekly Summaries")
        try:
            response = requests.get("http://localhost:8000/summaries")
            summaries = response.json()
            if summaries:
                df = pd.DataFrame(summaries)
                st.dataframe(df)
            else:
                st.info("No summaries found")
        except:
            st.error("Could not connect to the API")

elif page == 'Import Data':
    st.header("Import Workout Data")
    
    # Initialize session state for workouts if not exists
    if 'current_workouts' not in st.session_state:
        st.session_state.current_workouts = None
    
    # File upload section
    st.subheader("Upload Training Peaks Export")
    col1, col2 = st.columns(2)
    with col1:
        workouts_file = st.file_uploader(
            "Upload Workouts CSV",
            type=['csv'],
            key="workouts_csv_uploader"
        )
    with col2:
        metrics_file = st.file_uploader(
            "Upload Metrics CSV",
            type=['csv'],
            key="metrics_csv_uploader"
        )

    st.subheader("Upload Workout Files")
    fit_files = st.file_uploader(
        "Upload FIT Files (Zwift/Garmin)",
        type=['fit', 'fit.gz'],
        accept_multiple_files=True,
        key="fit_files_uploader"
    )
    
    if fit_files:
        st.subheader("Workout Analysis")
        
        # Create tabs for each FIT file
        file_tabs = st.tabs([f"Workout {i+1}: {fit_file.name}" for i, fit_file in enumerate(fit_files)])
        
        for fit_file, tab in zip(fit_files, file_tabs):
            with tab:
                try:
                    files = {'file': fit_file}
                    response = requests.post(
                        "http://localhost:8000/upload/fit",
                        files=files
                    )
                    
                    if response.status_code == 200:
                        workout_data = response.json()['workout_data']
                        display_fit_file_analysis(fit_file, workout_data)
                    else:
                        error_detail = response.json().get('detail', 'Unknown error')
                        st.error(f"Error processing {fit_file.name}: {error_detail}")
                        st.write("Full error details:", str(error_detail))
                        
                except Exception as e:
                    st.error(f"Error processing {fit_file.name}: {str(e)}")
                    st.write("Full error details:", str(e))

    # Process workout file upload
    if workouts_file is not None and st.session_state.current_workouts is None:
        files = {'file': workouts_file}
        try:
            response = requests.post("http://localhost:8000/upload/workouts", files=files)
            if response.status_code == 200:
                st.session_state.current_workouts = response.json()['workouts']
                st.success(f"Successfully processed {len(st.session_state.current_workouts)} workouts!")
            else:
                st.error("Error processing workouts file")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    # Process metrics file
    if metrics_file is not None:
        files = {'file': metrics_file}
        try:
            response = requests.post("http://localhost:8000/upload/metrics", files=files)
            if response.status_code == 200:
                metrics = response.json()['metrics']
                st.success(f"Successfully processed {len(metrics)} metrics!")
                
                st.subheader("Metrics Summary")
                metrics_df = pd.DataFrame(metrics)
                st.dataframe(metrics_df)
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    # Clear data button
    if st.session_state.current_workouts is not None:
        if st.button("Clear Uploaded Data"):
            st.session_state.current_workouts = None
            st.experimental_rerun()
    
    # Display workouts and qualitative data form
    if st.session_state.current_workouts:
        st.subheader("Add Qualitative Data")
        
        for workout in st.session_state.current_workouts:
            unique_key = f"{workout['workout_day']}_{workout['title']}"
            
            with st.expander(f"{workout['workout_day']} - {workout['type']} ({workout['title']})"):
                with st.form(key=f"form_{unique_key}"):
                    # Pre-fill any existing data

                    athlete_comments = st.text_area(
                        "Athlete Comments",
                        value=workout.get('athlete_comments', ''),
                        key=f"comments_{unique_key}"
                    )
                    
                    # Show quantitative data for reference
                    st.write("Workout Details:")
                    if workout.get('power_data'):
                        st.write(f"- TSS: {workout['power_data'].get('tss', 'N/A')}")
                        st.write(f"- IF: {workout['power_data'].get('if', 'N/A')}")
                    
                    if workout.get('heart_rate_data'):
                        st.write(f"- Avg HR: {workout['heart_rate_data'].get('average', 'N/A')}")
                        st.write(f"- Max HR: {workout['heart_rate_data'].get('max', 'N/A')}")
                    
                    if workout.get('actual_duration'):
                        st.write(f"- Duration: {workout['actual_duration']:.1f} minutes")
                    
                    # Submit button for this workout's form
                    submit_button = st.form_submit_button("Save Notes")
                    if submit_button:
                        try:
                            response = requests.post(
                                "http://localhost:8000/workouts/qualitative",
                                json={
                                    "workout_day": workout['workout_day'],
                                    "workout_title": workout['title'],
                                    "athlete_comments": athlete_comments
                                }
                            )
                            
                            if response.status_code == 200:
                                st.success(f"Notes saved successfully for {workout['title']}!")
                            else:
                                st.error(f"Error saving notes: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error saving notes: {str(e)}")
    
    # Process metrics file
    if metrics_file is not None:
        files = {'file': metrics_file}
        try:
            response = requests.post("http://localhost:8000/upload/metrics", files=files)
            if response.status_code == 200:
                metrics = response.json()['metrics']
                st.success(f"Successfully processed {len(metrics)} metrics!")
                
                st.subheader("Metrics Summary")
                metrics_df = pd.DataFrame(metrics)
                st.dataframe(metrics_df)
        except Exception as e:
            st.error(f"Error: {str(e)}")

elif page == 'View Data':
    st.header("View Data")
    
    tab1, tab2 = st.tabs(["Workouts", "Weekly Summaries"])
    
    with tab1:
        try:
            response = requests.get("http://localhost:8000/workouts")
            if response.status_code == 200:
                workouts = response.json()
                if workouts:
                    df = pd.DataFrame(workouts)
                    st.dataframe(df)
                else:
                    st.info("No workouts found")
            else:
                st.error(f"Error fetching workouts: {response.status_code}")
        except Exception as e:
            st.error(f"Could not connect to the API: {str(e)}")
    
    with tab2:
        try:
            response = requests.get("http://localhost:8000/summaries")
            if response.status_code == 200:
                summaries = response.json()
                if summaries:
                    df = pd.DataFrame(summaries)
                    st.dataframe(df)
                else:
                    st.info("No weekly summaries found")
            else:
                st.error(f"Error fetching summaries: {response.status_code}")
        except Exception as e:
            st.error(f"Could not connect to the API: {str(e)}")

# In the Weekly Summary page section:
elif page == 'Proposed Workouts':
    st.header("Proposed Workouts")
    
    # File uploader
    uploaded_file = st.file_uploader("Upload Proposed Workouts JSON", type=["json"])
    
    if uploaded_file is not None:
        try:
            response = requests.post(
                "http://localhost:8000/upload/proposed_workouts",  # Adjust URL if needed
                files={"file": (uploaded_file.name, uploaded_file, "application/json")}
            )

            if response.status_code == 200:
                st.success("Successfully uploaded and saved proposed workouts!")
                st.json(response.json())
            else:
                st.error(f"Error processing the uploaded file: {response.json().get('detail', 'Unknown error')}")
        except requests.exceptions.RequestException as e:
            st.error(f"Error connecting to the API: {str(e)}")

# In the Weekly Summary page section:
elif page == 'Weekly Summary':
    st.header("Weekly Summary")
    
    # Date selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Week Start Date",
            value=datetime.now() - timedelta(days=7)
        )
    with col2:
        end_date = st.date_input(
            "Week End Date",
            value=datetime.now()
        )
    
    # Generate Summary button
    if st.button("Generate Summary") or st.session_state.show_notes_form:
        try:
            response = requests.get(
                f"http://localhost:8000/summary/generate",
                params={
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d')
                }
            )
            
            if response.status_code == 200:
                summary = response.json()
                st.session_state.current_summary = summary
                st.session_state.show_notes_form = True
                
                # Display summary using the display_weekly_summary function
                display_weekly_summary(summary)
                
                # Additional Notes Form
                st.subheader("Recovery Quality")
                with st.form("recovery_form"):
                    # Create two columns for a more organized layout
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("### Muscle Soreness Assessment")
                        
                        # Quick selection for common soreness areas
                        st.markdown("##### Quick Select Sore Areas")
                        soreness_areas = {
                            "Quads": st.checkbox("Quads"),
                            "Hamstrings": st.checkbox("Hamstrings"),
                            "Calves": st.checkbox("Calves"),
                            "Lower Back": st.checkbox("Lower Back"),
                            "Upper Back": st.checkbox("Upper Back"),
                            "Core": st.checkbox("Core"),
                            "Other": st.checkbox("Other")
                        }
                        
                        # Soreness severity slider
                        soreness_severity = st.slider(
                            "Overall Soreness Level",
                            min_value=1,
                            max_value=5,
                            value=1,
                            help="1 = No soreness, 5 = Severe soreness"
                        )
                        
                        # Additional soreness details
                        muscle_soreness_details = st.text_area(
                            "Additional Soreness Details",
                            help="Describe any specific patterns, triggers, or recovery observations",
                            height=100
                        )
                        
                        # Combine all soreness information
                        sore_areas = [area for area, checked in soreness_areas.items() if checked]
                        muscle_soreness = f"Severity: {soreness_severity}/5\n"
                        if sore_areas:
                            muscle_soreness += f"Areas: {', '.join(sore_areas)}\n"
                        if muscle_soreness_details:
                            muscle_soreness += f"Details: {muscle_soreness_details}"
                    
                    with col2:
                        st.markdown("### Fatigue Assessment")
                        
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
                            ]
                        )
                        
                        # Fatigue impact areas
                        st.markdown("##### Fatigue Impact")
                        fatigue_impacts = {
                            "Sleep Quality": st.checkbox("Affected Sleep Quality", key="sleep_quality"),
                            "Workout Performance": st.checkbox("Affected Workout Performance", key="workout_perf"),
                            "Daily Activities": st.checkbox("Affected Daily Activities", key="daily_activities"),
                            "Mental Focus": st.checkbox("Affected Mental Focus", key="mental_focus"),
                            "Recovery Time": st.checkbox("Needed Extra Recovery Time", key="recovery_time")
                        }
                        
                        # Additional fatigue details
                        fatigue_details = st.text_area(
                            "Additional Fatigue Details",
                            help="Describe any specific patterns or observations about your energy levels",
                            height=100
                        )
                        
                        # Combine all fatigue information
                        impact_areas = [area for area, checked in fatigue_impacts.items() if checked]
                        general_fatigue = f"Energy Pattern: {energy_pattern}\n"
                        if impact_areas:
                            general_fatigue += f"Impact Areas: {', '.join(impact_areas)}\n"
                        if fatigue_details:
                            general_fatigue += f"Details: {fatigue_details}"
                    
                    # Add a visual divider
                    st.markdown("---")
                    
                    # Preview section
                    with st.expander("Preview Your Recovery Notes"):
                        st.markdown("#### Muscle Soreness Patterns")
                        st.text(muscle_soreness)
                        st.markdown("#### General Fatigue Level")
                        st.text(general_fatigue)
                    
                    # Save button and handling
                    submitted = st.form_submit_button("Save Recovery Notes")
                    if submitted:
                        # Update session state
                        st.session_state.update({
                            'muscle_soreness': muscle_soreness,
                            'general_fatigue': general_fatigue,
                            'notes_saved': True
                        })
                        
                        # Add notes to current summary
                        current_summary = st.session_state.current_summary


                        # Create a properly formatted summary object
                        summary_data = {
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat(),
                            'total_tss': float(current_summary.get('total_tss', 0)),
                            'total_training_hours': float(current_summary.get('total_training_hours', 0)),
                            'sessions_completed': int(current_summary.get('sessions_completed', 0)),
                            'avg_sleep_quality': float(current_summary.get('avg_sleep_quality', 0)),
                            'avg_daily_energy': float(current_summary.get('avg_daily_energy', 0)),
                            'daily_energy': current_summary.get('daily_energy', {}),
                            'daily_sleep_quality': current_summary.get('daily_sleep_quality', {}),
                            'muscle_soreness_patterns': muscle_soreness,
                            'general_fatigue_level': general_fatigue,
                            'qualitative_feedback': current_summary.get('qualitative_feedback', []),
                            'workout_types': current_summary.get('workout_types', [])
                        }

                        try:
                            save_response = requests.post(
                                "http://localhost:8000/summary/save",
                                json=summary_data
                            )
                            if save_response.status_code == 200:
                                st.success("Recovery notes saved successfully!")
                            else:
                                st.error(f"Failed to save notes. Status code: {save_response.status_code}")
                                st.error(f"Error details: {save_response.text}")
                        except Exception as e:
                            st.error(f"Error saving notes: {str(e)}")
                            st.write("Debug - Full error details:", str(e))
                
                # Help text at the bottom of the form
                st.markdown("""
                    <div style='background-color: #e6e9ef; padding: 15px; border-radius: 5px; margin-top: 20px; border: 1px solid #c0c6d2;'>
                        <h4 style='color: #0e1117; margin-bottom: 10px;'>Tips for Detailed Recovery Assessment:</h4>
                        <ul style='color: #0e1117; margin-left: 20px;'>
                            <li style='margin-bottom: 5px;'>Use the checkboxes to quickly identify affected areas</li>
                            <li style='margin-bottom: 5px;'>The severity slider helps track soreness intensity over time</li>
                            <li style='margin-bottom: 5px;'>Add specific details in the text areas for better tracking</li>
                            <li style='margin-bottom: 5px;'>Preview your notes before saving to ensure completeness</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)


                # Only show export option if notes have been saved
                if st.session_state.notes_saved:
                    try:
                        export_response = requests.get(
                            "http://localhost:8000/summary/export",
                            params={
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat()
                            }
                        )
                        if export_response.status_code == 200:
                            export_data = export_response.json()
                            st.download_button(
                                label="Download Summary",
                                data=export_data['content'],
                                file_name=f"weekly_summary_{start_date.isoformat()}.txt",
                                mime="text/plain",
                                key="download_button"
                            )
                    except Exception as e:
                        st.error(f"Error preparing export: {str(e)}")
                
                # Add a reset button
                if st.button("Start New Summary"):
                    reset_form_state()
                    st.experimental_rerun()
                    
            else:
                st.error(f"Error generating summary: {response.json().get('detail', 'Unknown error')}")
                
        except Exception as e:
            st.error(f"Error generating summary: {str(e)}")