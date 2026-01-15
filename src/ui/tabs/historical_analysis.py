import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from src.storage.database import WorkoutDatabase
from src.utils.workout_visualizer import WorkoutVisualizer

def render_historical_analysis_tab():
    """Render the Historical Data tab content"""
    st.subheader("📊 Historical Workout Analyses")
    
    # Batch Sync & Analyze Section
    with st.expander("🔄 Batch Sync & Analyze (Date Range)", expanded=False):
        st.markdown("""
        Download and analyze multiple days of workouts in one session.
        This is more efficient than processing individual days.
        """)
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now().date() - timedelta(days=7),
                help="First day to download"
            )
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now().date(),
                help="Last day to download"
            )

        overwrite_existing = st.checkbox(
            "Overwrite existing analyses",
            value=False,
            help="Re-run AI analysis even if a workout already has analysis"
        )
        
        with col3:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("🚀 Sync & Analyze", type="primary"):
                if start_date > end_date:
                    st.error("Start date must be before end date")
                else:
                    # Run batch sync and analysis
                    try:
                        from src.utils.trainingpeaks_sync import TrainingPeaksSync
                        from src.utils.daily_auto_sync_and_analyze import DailyAutoSyncAndAnalyze
                        
                        with st.spinner(f"Syncing {start_date} to {end_date}..."):
                            # Step 1: Sync entire date range in one TrainingPeaks session
                            tp_sync = TrainingPeaksSync()
                            sync_results = tp_sync.run_sync(
                                start_date=start_date,
                                end_date=end_date,
                                cleanup_fit_files=False  # Keep files for analysis
                            )
                            
                            if not sync_results:
                                st.error("❌ TrainingPeaks sync failed. Check terminal output for details.")
                                return
                            
                            st.success(f"✅ Synced {sync_results.get('fit_files_uploaded', 0)} FIT files")
                        
                        # Step 2: Analyze all workouts in the range
                        with st.spinner("Analyzing workouts with AI..."):
                            # Show which model will be used
                            try:
                                from src.utils.gemini_model_discovery import get_best_free_models
                                free_models = get_best_free_models()
                                if free_models:
                                    st.info(f"🤖 Using free model: **{free_models[0]}** (cost: $0)")
                            except:
                                pass  # If model discovery fails, just continue
                            
                            automation = DailyAutoSyncAndAnalyze('data/fitness_data.db')
                            
                            # Analyze each day in the range
                            total_analyzed = 0
                            current_date = start_date
                            
                            progress_bar = st.progress(0)
                            total_days = (end_date - start_date).days + 1
                            
                            while current_date <= end_date:
                                progress = (current_date - start_date).days / total_days
                                progress_bar.progress(progress)
                                
                                # Analyze this day (skip sync since we already did it)
                                fit_files = automation.find_todays_fit_files(current_date)
                                
                                for fit_file in fit_files:
                                    # Analyze all workouts - FitFileAnalyzer handles non-cycling with placeholder
                                    try:
                                        analysis = automation.analyze_workout(fit_file)
                                        if analysis:
                                            automation.store_analysis(analysis)
                                            total_analyzed += 1
                                    except Exception as e:
                                        print(f"⚠️ Error analyzing {fit_file}: {e}")

                                # Also analyze workouts directly from the database (non-cycling + no FIT file)
                                try:
                                    db_results = automation.analyze_workouts_from_database(
                                        target_date=current_date,
                                        reanalyze_existing=overwrite_existing
                                    )
                                    total_analyzed += db_results.get('workouts_analyzed', 0)
                                except Exception as e:
                                    print(f"⚠️ Error analyzing DB workouts for {current_date}: {e}")
                                
                                current_date += timedelta(days=1)
                            
                            progress_bar.progress(1.0)
                            
                            # Cleanup temp files
                            automation.cleanup_temp_files()
                        
                        st.success(f"✅ Complete! Analyzed {total_analyzed} workouts from {start_date} to {end_date}")
                        st.info(f"💰 Cost: $0 (using free Gemini models)")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error during batch sync: {str(e)}")
                        import traceback
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())
    
    st.markdown("---")
    
    try:
        db = WorkoutDatabase('data/fitness_data.db')
        
        # Week navigation
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Calculate current week start (Monday)
            today = datetime.now().date()
            days_since_monday = today.weekday()
            current_week_start = today - timedelta(days=days_since_monday)
            
            # Allow selecting different weeks
            week_offset = st.number_input(
                "Weeks back from current",
                min_value=0,
                max_value=52,
                value=0,
                help="0 = current week, 1 = last week, etc."
            )
            
            selected_week_start = current_week_start - timedelta(weeks=week_offset)
            selected_week_end = selected_week_start + timedelta(days=6)
        
        with col2:
            st.metric("Week Start", selected_week_start.strftime("%b %d"))
        with col3:
            st.metric("Week End", selected_week_end.strftime("%b %d"))
        
        # Get analyses for the selected week
        analyses = db.get_historical_analyses(limit=200)  # Get more to filter by week
        
        # Filter to selected week
        week_analyses = []
        for a in analyses:
            try:
                workout_date_str = a.get('workout_date', '')
                if workout_date_str and workout_date_str != 'Unknown':
                    workout_date = datetime.strptime(workout_date_str, '%Y-%m-%d').date()
                    if selected_week_start <= workout_date <= selected_week_end:
                        week_analyses.append(a)
            except:
                pass
        
        if not week_analyses:
            st.info(f"No workouts found for week of {selected_week_start.strftime('%B %d, %Y')}. Try a different week or upload workouts.")
            return

        # Create a selection list with better workout titles
        # Use workout title from TrainingPeaks (cleaner than raw FIT filenames)
        # Sort by analyzed_at descending to get most recent first
        week_analyses.sort(key=lambda x: x.get('analyzed_at', ''), reverse=True)
        
        # Deduplicate - keep first (most recent) of each workout_id
        seen_workout_ids = set()
        seen_fallback_keys = set()
        options = []

        # Identify dates that have at least one non-generic title
        non_generic_dates = set()
        for a in week_analyses:
            title = a.get('title', 'Unknown Workout')
            date_str = a.get('workout_date', 'Unknown')
            if title and not title.startswith('Zwift Workout'):
                non_generic_dates.add(date_str)
        
        for a in week_analyses:
            workout_id = a.get('workout_id')
            if workout_id and workout_id in seen_workout_ids:
                continue  # Skip duplicate
            
            if workout_id:
                seen_workout_ids.add(workout_id)
            
            date_str = a['workout_date'] if a['workout_date'] != 'Unknown' else a['analyzed_at'][:10]
            
            # Use TrainingPeaks workout title (from workouts table) instead of FIT filename
            title = a.get('title', 'Unknown Workout')

            # Skip generic Zwift workout entries when a better title exists for the same date
            if (not workout_id) and title.startswith('Zwift Workout') and date_str in non_generic_dates:
                continue
            
            # Clean up the title for better display
            if title.startswith('Zwift - '):
                # Remove redundant "Zwift - " prefix and long venue names
                title_parts = title.replace('Zwift - ', '').split(' on ')
                title = title_parts[0]  # Just the workout name, not the Zwift world/route
            
            display_key = f"{date_str} - {title}"

            # Fallback dedupe for entries without workout_id
            fallback_key = f"{date_str}:{title}"
            if not workout_id:
                if fallback_key in seen_fallback_keys:
                    continue
                seen_fallback_keys.add(fallback_key)
            options.append((display_key, a))
        
        # Sort options by date (newest first)
        options.sort(key=lambda x: x[0], reverse=True)
        
        st.markdown(f"**{len(options)} workout(s) this week**")
        
        selected_option = st.selectbox(
            "Select a workout to view analysis:",
            options=[opt[0] for opt in options],
            index=0
        )
        
        # Find the selected analysis
        selected_analysis = None
        for display_key, analysis in options:
            if display_key == selected_option:
                selected_analysis = analysis
                break
        
        if selected_analysis:
            analysis = selected_analysis
            
            # Display the analysis
            st.markdown("---")
            st.markdown(f"### 🚴 {analysis['title']}")
            st.caption(f"Date: {analysis['workout_date']} | Analyzed: {analysis['analyzed_at']}")
            
            # Create tabs for this specific workout view
            view_tabs = st.tabs(["📈 Visualization", "🤖 AI Insights", "⚡ Peak Efforts", "📝 Raw Data"])
            
            with view_tabs[0]:
                # Visualization
                if analysis.get('fit_data'):
                    try:
                        visualizer = WorkoutVisualizer()
                        # Parse fit_data if it's a string, otherwise use as is
                        fit_data = analysis['fit_data']
                        if isinstance(fit_data, str):
                            fit_data = json.loads(fit_data)
                            
                        peak_efforts = analysis.get('peak_efforts', {})
                        
                        fig = visualizer.create_workout_dashboard(fit_data, peak_efforts)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Power Curve
                        if peak_efforts:
                            st.markdown("#### Power Curve")
                            curve_fig = visualizer.create_peak_power_curve(peak_efforts)
                            st.plotly_chart(curve_fig, use_container_width=True)
                            
                    except Exception as e:
                        st.error(f"Error creating visualization: {str(e)}")
                else:
                    st.warning("No FIT file data available for visualization.")
            
            with view_tabs[1]:
                # AI Analysis Text
                st.markdown(analysis['analysis_text'])
                
            with view_tabs[2]:
                # Peak Efforts Table
                peak_efforts = analysis.get('peak_efforts', {})
                if peak_efforts:
                    # Convert to DataFrame for nice display
                    data = []
                    for duration, details in peak_efforts.items():
                        data.append({
                            "Duration": duration,
                            "Power (W)": f"{details['power']:.0f}",
                            "HR (bpm)": f"{details.get('heart_rate', 'N/A')}"
                        })
                    
                    df = pd.DataFrame(data)
                    st.table(df)
                else:
                    st.info("No peak efforts recorded for this workout.")
            
            with view_tabs[3]:
                # Raw Data
                with st.expander("View Analysis JSON"):
                    st.json(analysis)

    except Exception as e:
        st.error(f"Error loading historical data: {str(e)}")
