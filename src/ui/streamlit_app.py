# src/ui/streamlit_app.py

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import requests
import json
import plotly.express as px

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

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ['Dashboard', 'Import Data', 'Weekly Summary', 'View Data', 'Debug Upload'])

# Main content
st.title("Fitness Tracker")

if page == 'Dashboard':
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
                    how_it_felt = st.text_area(
                        "How did it feel?",
                        value=workout.get('how_it_felt', ''),
                        key=f"felt_{unique_key}"
                    )
                    
                    technical_issues = st.text_area(
                        "Any technical issues?",
                        value=workout.get('technical_issues', ''),
                        key=f"tech_{unique_key}"
                    )
                    
                    modifications = st.text_area(
                        "Any modifications made?",
                        value=workout.get('modifications', ''),
                        key=f"mod_{unique_key}"
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
                                    "how_it_felt": how_it_felt,
                                    "technical_issues": technical_issues,
                                    "modifications": modifications
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

elif page == 'Debug Upload':
    st.header("Debug CSV Upload")
    st.write("Use this page to examine the data in your CSV file")
    
    uploaded_file = st.file_uploader("Upload workout CSV for analysis", type=['csv'])
    
    if uploaded_file:
        try:
            files = {'file': uploaded_file}
            response = requests.post("http://localhost:8000/debug/workout_upload", files=files)
            
            if response.status_code == 200:
                debug_data = response.json()
                
                st.subheader("CSV Overview")
                st.write(f"Total columns: {len(debug_data['columns'])}")
                st.write(f"Total rows: {debug_data['row_count']}")
                
                st.subheader("Column Analysis")
                for column in debug_data['columns']:
                    stats = debug_data['column_stats'][column]
                    with st.expander(f"Column: {column}"):
                        st.write(f"Data type: {stats['dtype']}")
                        st.write(f"Non-null values: {stats['non_null_count']}")
                        st.write(f"Unique values: {stats['unique_values']}")
                        st.write(f"Has null values: {stats['has_nulls']}")
                        st.write("Sample values:")
                        for val in stats['sample_values']:
                            st.write(f"  - {val}")
                
                st.subheader("Sample Rows")
                df = pd.DataFrame(debug_data['sample_rows'])
                st.dataframe(df)
                
            else:
                st.error("Error analyzing CSV file")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")

# In the Weekly Summary page section:
# Update the Weekly Summary section
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
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )
            
            if response.status_code == 200:
                summary = response.json()
                st.session_state.current_summary = summary
                st.session_state.show_notes_form = True
                
                # Display summary using the display_weekly_summary function
                display_weekly_summary(summary)
                
                # Additional Notes Form
                st.subheader("Additional Notes")
                with st.form("notes_form"):
                    sleep_notes = st.text_area(
                        "Sleep notes for the week",
                        value=st.session_state.get('sleep_notes', ''),
                        height=150
                    )
                    
                    equipment_issues = st.text_area(
                        "Equipment Issues",
                        value=st.session_state.get('equipment_issues', '')
                    )
                    
                    nutrition_concerns = st.text_area(
                        "Nutrition Concerns",
                        value=st.session_state.get('nutrition_concerns', '')
                    )
                    
                    other_factors = st.text_area(
                        "Other Relevant Factors",
                        value=st.session_state.get('other_factors', '')
                    )
                    
                    submitted = st.form_submit_button("Save Notes")
                    if submitted:
                        # Update session state
                        st.session_state.update({
                            'sleep_notes': sleep_notes,
                            'equipment_issues': equipment_issues,
                            'nutrition_concerns': nutrition_concerns,
                            'other_factors': other_factors,
                            'notes_saved': True
                        })
                        
                        # Add notes to current summary
                        current_summary = st.session_state.current_summary
                        current_summary.update({
                            'sleep_notes': sleep_notes,
                            'equipment_issues': equipment_issues,
                            'nutrition_concerns': nutrition_concerns,
                            'other_factors': other_factors
                        })
                        
                        try:
                            save_response = requests.post(
                                "http://localhost:8000/summary/save",
                                json=current_summary
                            )
                            if save_response.status_code == 200:
                                st.success("Notes saved successfully!")
                            else:
                                st.error("Failed to save notes")
                        except Exception as e:
                            st.error(f"Error saving notes: {str(e)}")
                
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