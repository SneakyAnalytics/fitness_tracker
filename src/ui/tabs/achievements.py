"""
🏆 Achievements & Milestones Tab
=================================
Visualize athlete achievements and goals over time.

**NEW: Milestone Visualization Enhancement**
- Timeline view of categorized achievements
- Goal tracking with progress
- Pattern insights display
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd


def render_achievements_tab():
    """
    Render the achievements and milestones visualization tab.
    
    Shows:
    - Achievement timeline (by category)
    - Active goals with priorities
    - Multi-week pattern insights
    - Sentiment trends
    """
    from src.utils.coaching_notes import CoachingNotesManager
    
    st.header("🏆 Achievements & Milestones")
    st.markdown("*Track your progress, celebrate wins, and stay focused on goals*")
    
    # Load coaching notes
    manager = CoachingNotesManager()
    
    # Create tabs for different views
    viz_tabs = st.tabs(["📅 Achievement Timeline", "⚡ Power PRs", "🎯 Active Goals", "📊 Pattern Insights"])
    
    # Tab 1: Achievement Timeline
    with viz_tabs[0]:
        render_achievement_timeline(manager)
    
    # Tab 2: Power PRs
    with viz_tabs[1]:
        render_power_achievements()
    
    # Tab 3: Active Goals
    with viz_tabs[2]:
        render_active_goals(manager)
    
    # Tab 4: Pattern Insights
    with viz_tabs[3]:
        render_pattern_insights(manager)


def render_achievement_timeline(manager: 'CoachingNotesManager'):
    """Render timeline visualization of achievements."""
    st.subheader("Achievement Timeline")
    
    achievements = manager.achievements
    
    if not achievements:
        st.info("No achievements recorded yet. Complete milestones to see them here!")
        st.markdown("""
        **Achievements are auto-detected from feedback like:**
        - "Completed my first 100-mile ride"
        - "Hit a new FTP of 315W"
        - "Finished my first gran fondo"
        """)
        return
    
    # Convert to DataFrame
    ach_data = []
    for ach in achievements:
        ach_data.append({
            'Date': ach.date,
            'Description': ach.description,
            'Category': ach.category.capitalize(),
            'Value': ach.value or '',
            'Week': ach.week_number or 0
        })
    
    df = pd.DataFrame(ach_data)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    
    # Category selector
    categories = ['All'] + sorted(df['Category'].unique().tolist())
    selected_category = st.selectbox("Filter by category:", categories)
    
    if selected_category != 'All':
        df_filtered = df[df['Category'] == selected_category]
    else:
        df_filtered = df
    
    # Create timeline visualization
    if len(df_filtered) > 0:
        # Color mapping for categories
        category_colors = {
            'Distance': '#FF6B6B',
            'Power': '#4ECDC4',
            'Endurance': '#45B7D1',
            'Technical': '#FFA07A',
            'Event': '#98D8C8',
            'Consistency': '#C7CEEA'
        }
        
        fig = go.Figure()
        
        for category in df_filtered['Category'].unique():
            cat_data = df_filtered[df_filtered['Category'] == category]
            
            fig.add_trace(go.Scatter(
                x=cat_data['Date'],
                y=[category] * len(cat_data),
                mode='markers+text',
                name=category,
                marker=dict(
                    size=15,
                    color=category_colors.get(category, '#95A5A6'),
                    symbol='star',
                    line=dict(width=2, color='white')
                ),
                text=[desc[:30] + '...' if len(desc) > 30 else desc for desc in cat_data['Description']],
                textposition='top center',
                hovertemplate='<b>%{text}</b><br>Date: %{x}<br>Category: ' + category + '<extra></extra>',
                showlegend=True
            ))
        
        fig.update_layout(
            title="Achievement Timeline by Category",
            xaxis_title="Date",
            yaxis_title="Category",
            height=400,
            hovermode='closest',
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Achievement list
        st.subheader(f"All Achievements ({len(df_filtered)})")
        for _, row in df_filtered.iterrows():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**{row['Description']}**")
            with col2:
                st.badge(row['Category'], type="success")
            with col3:
                st.caption(row['Date'].strftime('%Y-%m-%d'))
    else:
        st.info(f"No achievements in '{selected_category}' category yet.")
    
    # Achievement stats
    st.subheader("Achievement Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Achievements", len(achievements))
    
    with col2:
        most_common_cat = df['Category'].mode()[0] if len(df) > 0 else "None"
        st.metric("Most Common Category", most_common_cat)
    
    with col3:
        if len(df) > 0:
            days_since_last = (datetime.now() - df['Date'].max()).days
            st.metric("Days Since Last Achievement", days_since_last)
        else:
            st.metric("Days Since Last Achievement", "N/A")


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


def render_active_goals(manager: 'CoachingNotesManager'):
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


def render_pattern_insights(manager: 'CoachingNotesManager'):
    """Render multi-week pattern analysis and sentiment trends."""
    st.subheader("Pattern Insights")
    
    # Multi-week pattern analysis
    weeks_back = st.slider("Analyze past N weeks:", min_value=2, max_value=12, value=6)
    patterns = manager.analyze_multi_week_patterns(weeks_back=weeks_back)
    
    if patterns['patterns_detected']:
        st.markdown(f"### Trends Over Past {patterns['weeks_analyzed']} Weeks")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📈 Power Trend**")
            trend = patterns['power_trend']
            if trend == 'improving':
                st.success("✅ Improving")
            elif trend == 'declining':
                st.warning("⚠️ Declining")
            else:
                st.info("➡️ Stable")
        
        with col2:
            st.markdown("**✅ Compliance Trend**")
            trend = patterns['compliance_trend']
            if trend == 'consistently_high':
                st.success("✅ Consistently High")
            elif trend == 'inconsistent':
                st.warning("⚠️ Inconsistent")
            else:
                st.info("➡️ Moderate")
        
        with col3:
            st.markdown("**💤 Recovery Trend**")
            trend = patterns['recovery_trend']
            if trend == 'strong':
                st.success("✅ Strong")
            elif trend == 'declining':
                st.warning("⚠️ Declining")
            else:
                st.info("➡️ Adequate")
        
        # Strengths and concerns
        col1, col2 = st.columns(2)
        
        with col1:
            if patterns['recurring_strengths']:
                st.markdown("### 💪 Recurring Strengths")
                for strength in patterns['recurring_strengths']:
                    st.success(f"✓ {strength}")
        
        with col2:
            if patterns['recurring_concerns']:
                st.markdown("### ⚠️ Areas to Monitor")
                for concern in patterns['recurring_concerns']:
                    st.warning(f"• {concern}")
        
        # Key insights
        if patterns['insights']:
            st.markdown("### 💡 Key Insights")
            for insight in patterns['insights']:
                st.info(insight)
    else:
        st.info("Insufficient data for pattern analysis. Keep training and providing feedback!")
    
    # Sentiment trends
    st.divider()
    st.subheader("Sentiment Trends")
    
    recent_obs = manager.get_recent_observations(n=10)
    sentiment_data = []
    
    for obs in recent_obs:
        if obs.sentiment:
            sentiment_data.append({
                'Week': obs.week_number,
                'Date': obs.date,
                'Sentiment': obs.sentiment.capitalize(),
                'Observation': obs.observation[:50] + '...' if len(obs.observation) > 50 else obs.observation
            })
    
    if sentiment_data:
        df_sentiment = pd.DataFrame(sentiment_data)
        
        # Sentiment distribution
        sentiment_counts = df_sentiment['Sentiment'].value_counts()
        
        fig = px.pie(
            values=sentiment_counts.values,
            names=sentiment_counts.index,
            title="Sentiment Distribution (Recent Weeks)",
            color=sentiment_counts.index,
            color_discrete_map={
                'Confident': '#2ECC71',
                'Positive': '#3498DB',
                'Neutral': '#95A5A6',
                'Negative': '#E74C3C',
                'Struggling': '#C0392B'
            }
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Recent sentiment timeline
        st.markdown("#### Recent Sentiment Timeline")
        for _, row in df_sentiment.iterrows():
            emoji_map = {
                'Confident': '💪',
                'Positive': '😊',
                'Neutral': '😐',
                'Negative': '😕',
                'Struggling': '😟'
            }
            emoji = emoji_map.get(row['Sentiment'], '📝')
            st.markdown(f"{emoji} **Week {row['Week']}** ({row['Date']}): {row['Sentiment']}")
            st.caption(row['Observation'])
    else:
        st.info("No sentiment data available yet. Sentiment is detected from your weekly feedback!")
