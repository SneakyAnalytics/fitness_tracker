"""
� Goals & Power PRs Tab
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd


class _GoalsView:
    """Adapter so the existing renderers read the SQLite goals table."""

    def get_goals_by_priority(self, status: str = 'active'):
        from types import SimpleNamespace
        from src.storage import goals as goals_store
        rows = goals_store.list_goals(include_inactive=(status != 'active'))
        return [SimpleNamespace(**{**g, 'category': g.get('category') or 'general'})
                for g in rows if g['status'] == status]


def render_goal_editor():
    """Fix dates/status by hand; the coach also updates goals via its tools."""
    from src.storage import goals as goals_store
    with st.expander("✏️ Edit goals"):
        for g in goals_store.list_goals(include_inactive=True):
            cols = st.columns([4, 2, 2, 1])
            cols[0].markdown(f"**#{g['id']}** {g['description']}" + (" ⚠️ date passed" if g['stale'] else ""))
            status = cols[1].selectbox("Status", goals_store.VALID_STATUSES,
                                       index=goals_store.VALID_STATUSES.index(g['status']),
                                       key=f"goal_status_{g['id']}", label_visibility="collapsed")
            target = cols[2].text_input("Target date", value=g['target_date'] or "", placeholder="YYYY-MM-DD",
                                        key=f"goal_date_{g['id']}", label_visibility="collapsed")
            if cols[3].button("Save", key=f"goal_save_{g['id']}"):
                try:
                    goals_store.update_goal(g['id'], status=status, target_date=target or None)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
        with st.form("add_goal"):
            st.markdown("**Add a goal or event**")
            desc = st.text_input("Description")
            c1, c2, c3 = st.columns(3)
            category = c1.selectbox("Category", ["event", "power", "endurance", "technical", "consistency", "body"])
            priority = c2.selectbox("Priority", [1, 2, 3, 4, 5], index=1,
                                    help="1 = A event (drives tapers), 2 = B event, 3+ = background goal")
            target_date = c3.text_input("Target date", placeholder="YYYY-MM-DD")
            if st.form_submit_button("Add") and desc:
                try:
                    goals_store.add_goal(desc, category, priority, target_date or None)
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))


def render_achievements_tab():
    """Render goals and power PRs tab."""
    st.header("🎯 Goals & Power PRs")

    viz_tabs = st.tabs(["🎯 Active Goals", "⚡ Power PRs"])

    with viz_tabs[0]:
        render_active_goals(_GoalsView())
        render_goal_editor()

    with viz_tabs[1]:
        render_power_achievements()


def render_power_achievements():
    """Render top power achievements/personal records."""
    from src.storage.database import WorkoutDatabase
    from src.utils.workout_visualizer import WorkoutVisualizer
    
    st.subheader("⚡ Peak Power Achievements")
    st.markdown("*Your all-time best power outputs across key durations*")
    
    try:
        db = WorkoutDatabase()
        
        # Get all personal bests
        personal_bests = db.get_personal_bests(athlete_id='default')
        
        if not personal_bests or not any(personal_bests.values()):
            st.info("No peak power records yet. Complete workouts to set your personal bests!")
            return
        
        # Standard power durations to display
        standard_durations = ['5s', '1min', '5min', '20min', '60min']
        
        # Display PRs in cards
        st.markdown("### 🏆 Personal Records")
        
        # Create rows of 3 columns each
        for i in range(0, len(standard_durations), 3):
            cols = st.columns(3)
            for j, duration in enumerate(standard_durations[i:i+3]):
                with cols[j]:
                    if duration in personal_bests and personal_bests[duration]:
                        pr = personal_bests[duration][0]  # Top record
                        
                        # Format power value
                        power = pr['effort_value']
                        
                        # Display as metric card
                        st.metric(
                            label=f"{duration} Peak Power",
                            value=f"{power:.0f}W",
                            delta=None
                        )
                        
                        # Show date and medal
                        medal = pr.get('medal', '')
                        date_str = pr['achieved_date']
                        try:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                            days_ago = (datetime.now() - date_obj).days
                            if days_ago == 0:
                                time_str = "Today"
                            elif days_ago == 1:
                                time_str = "Yesterday"
                            elif days_ago < 7:
                                time_str = f"{days_ago} days ago"
                            else:
                                time_str = date_obj.strftime('%b %d, %Y')
                        except:
                            time_str = date_str
                        
                        st.caption(f"{medal} {time_str}")
                    else:
                        # No record for this duration
                        st.metric(
                            label=f"{duration} Peak Power",
                            value="--",
                            delta=None
                        )
                        st.caption("No record set")
        
        # Top 3 for each duration
        st.divider()
        st.markdown("### 📊 Top 3 Efforts by Duration")
        
        # Duration selector
        available_durations = [d for d in standard_durations if d in personal_bests and personal_bests[d]]
        
        if available_durations:
            selected_duration = st.selectbox("Select duration:", available_durations)
            
            if selected_duration in personal_bests:
                top_efforts = personal_bests[selected_duration]
                
                # Create DataFrame
                data = []
                for effort in top_efforts:
                    data.append({
                        'Rank': f"{effort['medal']} #{effort['rank']}",
                        'Power (W)': f"{effort['effort_value']:.0f}",
                        'Date': effort['achieved_date']
                    })
                
                df = pd.DataFrame(data)
                st.table(df)
        
        # Power curve visualization
        st.divider()
        st.markdown("### 📈 Peak Power Curve")
        
        # Prepare data for power curve
        curve_data = []
        duration_seconds = {
            '5s': 5,
            '1min': 60,
            '5min': 300,
            '20min': 1200,
            '60min': 3600
        }
        
        for duration in standard_durations:
            if duration in personal_bests and personal_bests[duration]:
                pr = personal_bests[duration][0]
                curve_data.append({
                    'Duration (s)': duration_seconds.get(duration, 0),
                    'Duration': duration,
                    'Power (W)': pr['effort_value']
                })
        
        if curve_data:
            df_curve = pd.DataFrame(curve_data)
            df_curve = df_curve.sort_values('Duration (s)')
            
            # Create power curve chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_curve['Duration'],
                y=df_curve['Power (W)'],
                mode='lines+markers',
                name='Peak Power',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=10, color='#FF6B6B'),
                hovertemplate='<b>%{x}</b><br>Power: %{y:.0f}W<extra></extra>'
            ))
            
            fig.update_layout(
                title="Peak Power Curve (All-Time Best)",
                xaxis_title="Duration",
                yaxis_title="Power (W)",
                height=400,
                hovermode='x unified',
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Power stats
            st.markdown("### 📊 Power Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_power = df_curve['Power (W)'].mean()
                st.metric("Average Peak Power", f"{avg_power:.0f}W")
            
            with col2:
                max_power = df_curve['Power (W)'].max()
                st.metric("Highest Peak", f"{max_power:.0f}W")
            
            with col3:
                # Count total PRs
                total_prs = sum(len(efforts) for efforts in personal_bests.values())
                st.metric("Total PRs Set", total_prs)
        else:
            st.info("Not enough data to create power curve yet.")
    
    except Exception as e:
        st.error(f"Error loading power achievements: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


def render_active_goals(manager):
    """Render active goals with priorities."""
    st.subheader("Active Goals")
    
    active_goals = manager.get_goals_by_priority(status='active')
    
    if not active_goals:
        st.info("No active goals set. Add goals through weekly feedback!")
        st.markdown("""
        **Goals are auto-detected from feedback like:**
        - "My goal is to complete the C2C ride in June"
        - "I want to improve my FTP to 320W"
        - "Aiming for consistent 3-hour endurance rides"
        """)
        return
    
    # Group by priority
    priority_1 = [g for g in active_goals if g.priority == 1]
    priority_2 = [g for g in active_goals if g.priority == 2]
    priority_3 = [g for g in active_goals if g.priority == 3]
    
    # Display priority 1 goals (highest)
    if priority_1:
        st.markdown("### 🔥 Priority 1 Goals (Highest Priority)")
        for goal in priority_1:
            with st.container():
                st.markdown(f"#### {goal.description}")
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.caption(f"Category: {goal.category.capitalize()}")
                with col2:
                    if goal.target_date:
                        target_dt = datetime.strptime(goal.target_date, '%Y-%m-%d')
                        days_until = (target_dt - datetime.now()).days
                        if days_until > 0:
                            st.caption(f"⏰ {days_until} days until target")
                        else:
                            st.caption(f"⚠️ {abs(days_until)} days overdue")
                    else:
                        st.caption("Ongoing goal")
                with col3:
                    st.caption(f"Added: {goal.added_date}")
                
                if goal.progress_notes:
                    with st.expander("Progress Notes"):
                        for note in goal.progress_notes:
                            st.markdown(f"- {note}")
                st.divider()
    
    # Display priority 2 goals
    if priority_2:
        st.markdown("### ⭐ Priority 2 Goals")
        for goal in priority_2:
            st.markdown(f"**{goal.description}** ({goal.category.capitalize()})")
            if goal.target_date:
                st.caption(f"Target: {goal.target_date}")
            st.divider()
    
    # Display priority 3 goals
    if priority_3:
        with st.expander(f"📋 Priority 3 Goals ({len(priority_3)})"):
            for goal in priority_3:
                st.markdown(f"- {goal.description} ({goal.category.capitalize()})")
    
    # Goal summary metrics
    st.subheader("Goal Summary")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Active Goals", len(active_goals))
    with col2:
        st.metric("Priority 1 Goals", len(priority_1))
    with col3:
        event_goals = len([g for g in active_goals if g.category == 'event'])
        st.metric("Event Goals", event_goals)
    with col4:
        power_goals = len([g for g in active_goals if g.category == 'power'])
        st.metric("Power Goals", power_goals)

