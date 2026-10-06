"""
🎯 AI Coach Prompt Engineering
===============================
Constructs prompts for AI coaching system with cycling science knowledge.

🎓 EDUCATIONAL NOTE - Prompt Engineering Fundamentals:
------------------------------------------------------

**What is Prompt Engineering?**
The art/science of structuring input to get desired output from LLMs.

**Key Principles:**

1. **Structure Matters**
   - LLMs are pattern matchers - they respond to format cues
   - Clear sections → Clear outputs
   - Bad: "Make me a workout plan for next week"
   - Good: "# Task: Generate Workout Plan\n## Context: ...\n## Requirements: ..."

2. **Context Ordering**
   - Most important info FIRST (models have recency bias)
   - Order: System → Knowledge → Data → Task
   - Why: Attention mechanisms weight recent tokens higher

3. **Specificity**
   - Vague: "Make it challenging"
   - Specific: "4x8min at 95-100% FTP with 4min recovery"
   - LLMs need concrete boundaries

4. **Examples (Few-Shot Learning)**
   - Show desired format with examples
   - "Output like this: {...example JSON...}"
   - Dramatically improves format compliance

5. **Constraints & Guardrails**
   - Explicit limits prevent hallucination
   - "TSS must be between 300-600"
   - "Use only these workout types: [list]"

6. **Chain-of-Thought**
   - Ask LLM to "think step by step"
   - Improves reasoning quality
   - Example: "First analyze training load, then consider recovery needs, then generate plan"

**Our Approach:**
- Modular prompts (system, analysis, generation separate)
- Knowledge injection via RAG
- Structured output (JSON schema enforcement)
- Personality consistency (coaching voice)
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import json

# Import our RAG loader
try:
    from .rag_context_loader import RAGContextLoader
except ImportError:
    from rag_context_loader import RAGContextLoader


@dataclass
class PromptContext:
    """
    All data needed to construct a coaching prompt.
    
    Why we need this:
    - Organizes complex inputs
    - Makes prompt construction testable
    - Easy to extend with new data
    """
    athlete_profile: Dict
    coaching_notes: Dict
    weekly_summary: Dict
    comprehensive_context: Dict
    constraints: Optional[Dict] = None
    focus_topics: Optional[Set[str]] = None
    user_context: Optional[Dict] = None  # schedule_constraints, training_focus, week_feedback
    training_state: Optional[str] = None  # computed load/progression/readiness (coach_context)


class AICoachPrompts:
    """
    Constructs prompts for different AI coaching tasks.
    
    Educational note: Prompt Templates vs Dynamic Construction
    
    Templates (static):
    - Pro: Consistent, fast, easy to version control
    - Con: Inflexible, hard to customize per user
    
    Dynamic (what we use):
    - Pro: Adapts to athlete data, includes only relevant knowledge
    - Con: More complex, need careful testing
    
    Best practice: Hybrid approach
    - Templates for structure/voice
    - Dynamic for data/knowledge injection
    """
    
    def __init__(self, rag_loader: Optional[RAGContextLoader] = None):
        """
        Initialize with RAG context loader.
        
        Educational note: Dependency Injection
        - Could create RAGContextLoader here (tight coupling)
        - Better: Accept it as parameter (loose coupling, testable)
        - Enables: Testing with mock RAG, using different loaders
        """
        if rag_loader is None:
            rag_loader = RAGContextLoader()
        
        self.rag_loader = rag_loader
    
    def _build_system_prompt(self, personality: Dict) -> str:
        """
        Create the system/role prompt that defines AI coach personality.
        
        Educational note: System Prompts
        
        Purpose: Set the AI's role, tone, and behavioral guidelines
        
        Components:
        1. Identity: "You are an expert cycling coach..."
        2. Expertise: Credentials, knowledge areas
        3. Communication style: How to interact
        4. Constraints: What NOT to do
        5. Output format: How to structure responses
        
        Why it matters:
        - Primes the LLM's behavior for entire conversation
        - Consistent across all requests
        - Override with user prompts is harder (security)
        """
        
        style = personality.get('style', 'data-driven, encouraging, scientific')
        voice = personality.get('voice', 'professional yet approachable')
        approach = personality.get('approach', 'evidence-based with practical application')
        
        return f"""# Your Role: Expert Cycling Coach

You are an expert cycling coach specializing in endurance training and gravel racing. Your coaching philosophy is **{style}**, with a **{voice}** voice and an **{approach}** approach.

## Your Expertise
- Exercise physiology (VO2max, lactate threshold, power-based training)
- Periodization and training program design
- Gravel/endurance cycling specifics
- Indoor training (Zwift) and outdoor adaptation
- Recovery science and fatigue management
- Data analysis (power, heart rate, TSS, training load)

## Communication Principles
{self._format_list(personality.get('communication_preferences', [
    "Explain the 'why' behind recommendations",
    "Use data to support decisions",
    "Be encouraging while honest about challenges",
    "Acknowledge progress and improvements",
    "Provide actionable, specific guidance"
]))}

## Coaching Guidelines

### DO:
- Base decisions on athlete's historical data and current context
- Reference specific metrics (power, TSS, duration) from their training
- Provide progressive, sustainable training loads
- Explain scientific reasoning in accessible terms
- Consider seasonal preferences and life constraints
- Celebrate improvements and consistency

### DON'T:
- Make assumptions without data
- Prescribe excessive training volume or intensity
- Ignore signs of fatigue or declining performance
- Provide generic advice that doesn't fit the athlete
- Use overly technical jargon without explanation
- Recommend workouts that don't align with stated goals

## Output Requirements
- Be specific and actionable
- Reference actual data from the athlete's history
- Use proper cycling training terminology
- For workout plans: Follow JSON schema exactly
- For analysis: Provide clear observations and recommendations
"""
    
    def _format_list(self, items: List[str]) -> str:
        """Helper to format lists in markdown."""
        return "\n".join(f"- {item}" for item in items)
    
    def _build_athlete_context(self, context: PromptContext) -> str:
        """
        Format athlete profile and current state.
        
        Educational note: Data Presentation
        
        How you present data affects LLM understanding:
        
        Bad:  JSON dump: {"ftp": 300, "goals": [...]}
        Good: Structured narrative with headers
        
        Why:
        - LLMs trained on natural text, not raw JSON
        - Headers help with attention/retrieval
        - Narrative provides context for numbers
        """
        profile = context.athlete_profile
        
        sections = []
        sections.append("# Athlete Profile\n")
        
        sections.append(f"**Name:** {profile.get('name', 'Unknown')}")
        sections.append(f"**Current FTP:** {profile.get('current_ftp', 'Unknown')}W")
        
        if profile.get('starting_ftp'):
            improvement = profile['current_ftp'] - profile['starting_ftp']
            sections.append(f"**FTP Progression:** +{improvement}W from {profile['starting_ftp']}W baseline")
        
        # Goals and training phase deliberately omitted here: goals come only from the
        # goals table (with dates/status) and the week type from the computed training
        # state. The old free-text primary_goals list and phase label went stale and
        # made the coach bring up finished goals.
        
        # Seasonal preferences
        if profile.get('seasonal_preferences'):
            sections.append("\n## Seasonal Activity Preferences")
            for season, activities in profile['seasonal_preferences'].items():
                sections.append(f"- **{season.title()}:** {activities}")
        
        return "\n".join(sections)
    
    def _build_training_context(self, context: PromptContext) -> str:
        """
        Format recent training history and trends.
        
        Educational note: Information Density
        
        Challenge: Lots of data, limited tokens
        Solution: Summarize + highlight key patterns
        
        Structure:
        1. High-level summary (quick scan)
        2. Key metrics (quantitative)
        3. Trends (direction of change)
        4. Notable observations (qualitative)
        """
        comp_ctx = context.comprehensive_context
        sections = []
        
        sections.append("# Recent Training Context\n")
        
        # Weekly summary
        if context.weekly_summary:
            ws = context.weekly_summary
            sections.append(f"## Most Recent Week ({ws.get('start_date')} to {ws.get('end_date')})")
            sections.append(f"- **Total TSS:** {ws.get('total_tss', 0):.1f}")
            sections.append(f"- **Training Hours:** {ws.get('total_training_hours', 0):.1f}")
            sections.append(f"- **Sessions Completed:** {ws.get('sessions_completed', 0)}")

            # Power zone distribution + average watts
            zone_dist = ws.get('power_zone_distribution') or {}
            zone_avg = ws.get('power_zone_avg_watts') or {}
            if zone_dist:
                sections.append("- **Power Zone Distribution (time %):**")
                for zone, pct in zone_dist.items():
                    avg_watts = zone_avg.get(zone)
                    if avg_watts is not None:
                        sections.append(f"  - {zone}: {pct:.1f}% (avg {avg_watts:.0f}W)")
                    else:
                        sections.append(f"  - {zone}: {pct:.1f}%")
            
            # Workout type distribution for the week
            if ws.get('qualitative_feedback'):
                workout_types = {}
                athlete_comments_list = []
                for workout in ws['qualitative_feedback']:
                    wtype = workout.get('type', 'Unknown')
                    workout_types[wtype] = workout_types.get(wtype, 0) + 1
                    
                    # Collect athlete comments/feedback
                    feedback = workout.get('feedback', {})
                    athlete_comment = feedback.get('athlete_comments')
                    if athlete_comment and athlete_comment.strip():
                        workout_day = workout.get('date', 'Unknown date')
                        workout_title = workout.get('title', 'Unknown workout')
                        athlete_comments_list.append(f"  - **{workout_day} ({workout_title}):** {athlete_comment}")
                
                sections.append(f"- **Workout Types:** {', '.join(f'{t}: {c}' for t, c in workout_types.items())}")
                
                # Add athlete comments section if any exist
                if athlete_comments_list:
                    sections.append("\n### Athlete Comments & Feedback")
                    sections.append("*The athlete provided these comments about specific workouts:*\n")
                    sections.extend(athlete_comments_list)
            
            # AI Workout Analyses (Gemini coaching insights)
            if ws.get('ai_workout_analyses'):
                sections.append("\n### AI Workout Analyses")
                sections.append("*Detailed AI coaching analysis from each workout's FIT file data:*\n")
                
                for analysis in ws['ai_workout_analyses']:
                    workout_name = analysis.get('workout_name', 'Unknown')
                    workout_date = analysis.get('workout_date', 'Unknown')
                    
                    sections.append(f"\n**{workout_date} - {workout_name}**")
                    
                    # Analysis data (quality, insights, recovery)
                    analysis_data = analysis.get('analysis_data', {})
                    
                    # Handle case where analysis_data might be a JSON string
                    if isinstance(analysis_data, str):
                        try:
                            import json
                            analysis_data = json.loads(analysis_data)
                        except:
                            analysis_data = {}
                    
                    if analysis_data and isinstance(analysis_data, dict):
                        if analysis_data.get('quality_rating'):
                            sections.append(f"  - Quality Rating: {analysis_data['quality_rating']}/10")
                        if analysis_data.get('effort_distribution'):
                            sections.append(f"  - Effort Distribution: {analysis_data['effort_distribution']}")
                        if analysis_data.get('recovery_recommendations'):
                            sections.append(f"  - Recovery: {analysis_data['recovery_recommendations']}")
                        if analysis_data.get('performance_insights'):
                            sections.append(f"  - Insights: {analysis_data['performance_insights']}")
                    
                    # Peak efforts
                    peak_efforts = analysis.get('peak_efforts', {})
                    if peak_efforts:
                        # Handle both old format (power as number) and new format (power as dict with 'power' key)
                        efforts_list = []
                        for dur, power_data in peak_efforts.items():
                            if isinstance(power_data, dict):
                                power = power_data.get('power', 0)
                            else:
                                power = power_data
                            
                            if power:
                                efforts_list.append(f"{dur}: {int(power)}W")
                        
                        if efforts_list:
                            efforts_str = ", ".join(efforts_list)
                            sections.append(f"  - Peak Powers: {efforts_str}")
                    
                    # Full analysis text if available
                    analysis_text = analysis.get('analysis_text', '')
                    if analysis_text and len(analysis_text) > 100:
                        sections.append(f"  - Full Analysis: {analysis_text[:500]}...")
        
        # Compliance
        if comp_ctx.get('workout_compliance'):
            compliance = comp_ctx['workout_compliance']
            sections.append(f"\n## 4-Week Compliance")
            sections.append(f"- **Overall:** {compliance['overall_compliance_pct']}% ({compliance['total_completed']}/{compliance['total_planned']} workouts)")
        
        # Workout type distribution
        if comp_ctx.get('workout_type_distribution'):
            dist = comp_ctx['workout_type_distribution']
            sections.append(f"\n## Workout Type Distribution (Last {dist['weeks_analyzed']} Weeks)")
            for wtype, count in sorted(dist['distribution'].items(), key=lambda x: x[1], reverse=True):
                pct = dist['distribution_pct'].get(wtype, 0)
                sections.append(f"- **{wtype}:** {count} workouts ({pct:.1f}%)")
        
        # Key progressions
        if comp_ctx.get('workout_type_progressions'):
            # Get weeks analyzed from first progression entry
            weeks_analyzed = next(iter(comp_ctx['workout_type_progressions'].values())).get('weeks_analyzed', 8)
            sections.append(f"\n## Workout-Specific Trends (Last {weeks_analyzed} Weeks)")
            for wtype, analysis in comp_ctx['workout_type_progressions'].items():
                if analysis.get('count', 0) > 0:
                    sections.append(f"\n### {wtype}")
                    sections.append(f"- **Count:** {analysis['count']} workouts")
                    
                    # Note structured/ERG workouts so the AI understands power = prescribed
                    structured = analysis.get('structured_count', 0)
                    total = analysis['count']
                    if structured > 0:
                        sections.append(
                            f"- **ERG/Structured:** {structured}/{total} workouts executed on "
                            f"smart trainer in ERG mode — power values reflect prescribed targets, "
                            f"not free-ride effort. Consistent power is expected and correct."
                        )

                    # Note if any incomplete workouts were filtered
                    if analysis.get('filtered_incomplete', 0) > 0:
                        sections.append(f"- **Note:** {analysis['filtered_incomplete']} incomplete workout(s) excluded for data quality")
                    
                    if analysis.get('averages'):
                        # For ERG/structured workout types, TSS and duration vary by design
                        # (different workout recipes each week). Only power trend is meaningful.
                        # Showing TSS/duration as "declining" misleads the AI into false conclusions.
                        fully_structured = (structured > 0 and structured == total)
                        power_types = ['VO2max', 'Threshold', 'Tempo']
                        suppress_tss_duration = fully_structured and wtype in power_types

                        # Human-readable labels for metric keys
                        metric_labels = {
                            'avg_power': 'Normalized Power (NP, fitness trend metric)',
                            'interval_power': 'Work Interval Power (VO2/threshold zone watts, varies by prescription)',
                            'normalized_power': None,  # skip — same as avg_power now
                            'tss': 'TSS',
                            'duration_hours': 'Duration (hrs)',
                            'intensity_factor': 'Intensity Factor',
                            'avg_hr': 'Avg HR',
                        }
                        # For ERG workouts, interval_power varies by %FTP prescription
                        # (e.g. one week targets 110% FTP, next targets 117% FTP) — identical
                        # to how TSS varies. Trending it misleads the AI into thinking fitness
                        # is declining when the plan just assigned a lighter prescription.
                        suppress_no_trend = {'tss', 'duration_hours', 'interval_power'} if suppress_tss_duration else {'tss', 'duration_hours'}

                        shown = 0
                        for metric, value in analysis['averages'].items():
                            label = metric_labels.get(metric, metric)
                            if label is None:
                                continue  # skip redundant metrics
                            if metric in suppress_no_trend:
                                # Show value but omit the trend label to avoid misleading the AI
                                sections.append(f"- **{label}:** {value:.1f} [varies by workout design — not a fitness indicator]")
                                shown += 1
                                continue
                            trend = analysis['trends'].get(metric, 'stable')
                            trend_emoji = {'improving': '📈', 'declining': '📉', 'stable': '➡️'}.get(trend, '')
                            sections.append(f"- **{label}:** {value:.1f}W [{trend} {trend_emoji}]")
                            shown += 1
                            if shown >= 4:
                                break
        
        # Power trends
        if comp_ctx.get('power_trends'):
            power = comp_ctx['power_trends']
            if power.get('latest_avg_power'):
                sections.append(f"\n## Power Trends")
                sections.append(f"- **Latest Avg Power:** {power['latest_avg_power']:.0f}W")
                sections.append(f"- **Trend:** {power['trend']}")
        
        return "\n".join(sections)
    
    def _build_coaching_observations(self, coaching_notes: Dict) -> str:
        """
        Format coaching observations for continuity.
        
        Educational note: Memory/State Management
        
        Challenge: LLMs are stateless (no memory between calls)
        Solution: Inject previous observations into prompt
        
        This creates "memory" by:
        1. Storing past observations in coaching_notes.json
        2. Loading them into each prompt
        3. AI sees its own past recommendations
        
        Result: Continuity across weeks (not making contradictory suggestions)
        """
        sections = []
        sections.append("# Coaching Observations & History\n")
        
        # Previous week's continuity (AI's memory of what to focus on)
        continuity = coaching_notes.get('coaching_continuity', [])
        if continuity:
            # Get most recent continuity
            last_week = continuity[-1] if continuity else None
            sections.append(f"## Continuity Notes (week of {last_week.get('week_start_date', 'unknown')})")
            sections.append("*Your observations and priorities from the most recent coaching session:*\n")
            if last_week:
                if last_week.get('key_observations'):
                    sections.append("**Key Observations:**")
                    for obs in last_week['key_observations']:
                        sections.append(f"- {obs}")
                    sections.append("")
                
                if last_week.get('progression_notes') or last_week.get('progression'):
                    sections.append("**Progression Notes:**")
                    for prog in last_week.get('progression_notes') or last_week.get('progression'):
                        sections.append(f"- {prog}")
                    sections.append("")
                
                if last_week.get('areas_to_monitor') or last_week.get('monitor'):
                    sections.append("**Areas to Monitor:**")
                    for area in last_week.get('areas_to_monitor') or last_week.get('monitor'):
                        sections.append(f"- {area}")
                    sections.append("")
                
                if last_week.get('next_week_priorities') or last_week.get('next_priorities'):
                    sections.append("**Priorities for This Week:**")
                    for priority in last_week.get('next_week_priorities') or last_week.get('next_priorities'):
                        sections.append(f"- {priority}")
                    sections.append("")
                
                if last_week.get('recurring_schedule'):
                    sections.append("**Recurring Schedule:**")
                    for day, activity in last_week['recurring_schedule'].items():
                        sections.append(f"- {day}: {activity}")
                    sections.append("")
        
        # Recent observations (legacy format - keep for compatibility)
        observations = coaching_notes.get('observations', [])
        if observations:
            sections.append("## Additional Weekly Observations")
            # Show last 2 observations
            for obs in observations[-2:]:
                sections.append(f"\n### Week {obs.get('week_number')} ({obs.get('date')})")
                sections.append(f"**Observation:** {obs.get('observation', 'None')}")
                if obs.get('focus_areas'):
                    sections.append(f"**Focus Areas:** {', '.join(obs['focus_areas'])}")
                if obs.get('athlete_response'):
                    sections.append(f"**Athlete Response:** {obs['athlete_response']}")
        
        # (The old 'next_week_focus' string is superseded by the dated continuity
        # notes above; it was last written months ago.)
        
        return "\n".join(sections)

    def _build_goals_context(self, goals: List[Dict]) -> str:
        """
        Format athlete goals with urgency/timeline so the coach can naturally
        reference upcoming events, prioritise relevant training, and avoid
        re-asking about things the athlete has already stated.
        """
        from datetime import date as _date

        today = _date.today()

        active = [g for g in goals if g.get('status', 'active') == 'active']
        if not active:
            return ""

        sections = ["# Training Goals & Event Timeline\n"]
        sections.append(
            "Use this context to proactively reference the athlete's events and goals "
            "without asking them to re-explain them. Build each week's plan with event "
            "proximity and goal priority in mind.\n"
        )

        # Bucket goals
        imminent, upcoming, later, ongoing = [], [], [], []
        for g in active:
            td = g.get('target_date')
            if td:
                try:
                    target = _date.fromisoformat(td)
                    days_away = (target - today).days
                    if days_away < 0:
                        days_away = 0  # already past — show as 0
                    g['_days_away'] = days_away
                    if days_away <= 28:
                        imminent.append(g)
                    elif days_away <= 84:
                        upcoming.append(g)
                    else:
                        later.append(g)
                except ValueError:
                    ongoing.append(g)
            else:
                ongoing.append(g)

        def _fmt_goal(g: Dict, show_urgency: bool = True) -> List[str]:
            lines = []
            days = g.get('_days_away')
            if show_urgency and days is not None:
                if days == 0:
                    urgency = "⚠️ **PAST DUE / THIS WEEK**"
                elif days <= 14:
                    urgency = f"🔥 **{days} days away**"
                elif days <= 28:
                    urgency = f"⚡ **{days} days away** (~{days // 7} weeks)"
                else:
                    urgency = f"📅 {days} days away (~{days // 7} weeks)"
                lines.append(f"- **{g['description']}** — {urgency}")
            else:
                prefix = "🎯" if g.get('priority', 3) <= 1 else "⭐"
                lines.append(f"- {prefix} **{g['description']}**")
            notes = g.get('progress_notes') or []
            for note in notes[-2:]:  # most recent 2
                lines.append(f"  - _{note}_")
            return lines

        if imminent:
            sections.append("## 🔥 Imminent Events (within 4 weeks)")
            for g in sorted(imminent, key=lambda x: x['_days_away']):
                sections.extend(_fmt_goal(g))
            sections.append("")

        if upcoming:
            sections.append("## ⚡ Upcoming Events (4–12 weeks)")
            for g in sorted(upcoming, key=lambda x: x['_days_away']):
                sections.extend(_fmt_goal(g))
            sections.append("")

        if later:
            sections.append("## 📅 Later This Season (>12 weeks)")
            for g in sorted(later, key=lambda x: x['_days_away']):
                sections.extend(_fmt_goal(g))
            sections.append("")

        if ongoing:
            sections.append("## 🏋️ Ongoing Performance Goals")
            for g in sorted(ongoing, key=lambda x: x.get('priority', 3)):
                sections.extend(_fmt_goal(g, show_urgency=False))
            sections.append("")

        return "\n".join(sections)

    def _build_tss_baseline_guidance(self, weekly_summaries: List[Dict]) -> str:
        """
        Provide AI with multi-week TSS context to establish proper baseline.
        Helps avoid using anomaly weeks (travel, illness) as baseline.
        """
        sections = []
        sections.append("# Multi-Week TSS Baseline (for Load Planning)\n")
        sections.append("**CRITICAL:** Use this data to establish realistic TSS target for next week.\n")
        sections.append("**DO NOT** base next week's TSS solely on last week if it was an anomaly (travel, illness, etc.)\n")
        
        if weekly_summaries and len(weekly_summaries) > 0:
            sections.append("\n## Last 4 Weeks TSS History:")
            
            tss_values = []
            for i, week in enumerate(weekly_summaries[:4], 1):
                week_tss = week.get('total_tss', 0)
                week_workouts = week.get('total_workouts', 0)
                week_start = week.get('week_start', 'Unknown')
                
                # Identify potential anomaly weeks (very low TSS or very few workouts)
                is_anomaly = week_tss < 250 or week_workouts < 4
                anomaly_flag = " ⚠️ LIKELY ANOMALY (travel/illness/off-week)" if is_anomaly else ""
                
                sections.append(f"  {i}. Week of {week_start}: {week_tss:.0f} TSS ({week_workouts} workouts){anomaly_flag}")
                
                # Only include non-anomaly weeks in average calculation
                if not is_anomaly:
                    tss_values.append(week_tss)
            
            # Calculate baseline from non-anomaly weeks
            if tss_values:
                avg_tss = sum(tss_values) / len(tss_values)
                sections.append(f"\n**BASELINE (excluding anomaly weeks):** {avg_tss:.0f} TSS/week (average of {len(tss_values)} normal weeks)")
                sections.append(f"**RECOMMENDED NEXT WEEK TSS RANGE:** {avg_tss*0.9:.0f}-{avg_tss*1.15:.0f} TSS")
                sections.append("  - Lower end (-10%): Coming off hard block or need recovery")
                sections.append("  - Mid range: Maintain current load")
                sections.append("  - Upper end (+15%): Progressive overload, building fitness")
            else:
                sections.append("\n⚠️ All recent weeks appear to be anomalies - use 400-500 TSS as default baseline")
        
        sections.append("\n**NEVER blindly copy last week's TSS if it was an anomaly week!**")
        
        return "\n".join(sections)
    
    def _build_user_context_section(self, user_context: Dict) -> str:
        """
        Format user-provided weekly context (schedule, focus, feedback).
        
        This is the interactive element where users provide weekly input:
        - Schedule constraints (races, work conflicts, travel, etc.)
        - Training focus for upcoming week
        - Feedback on how they're feeling
        
        CRITICAL: This input has TWO contexts depending on when it was entered:
        1. ANALYSIS MODE: Athlete is describing "the week that just finished" (retrospective)
        2. GENERATION MODE: Athlete is describing "next week's upcoming schedule" (prospective)
        
        The function caller must clarify which context applies!
        """
        sections = []
        
        # Determine if this is for analysis (past week) or generation (upcoming week)
        is_upcoming_week = user_context.get('context_type') == 'upcoming_week' if user_context else False
        
        if is_upcoming_week:
            sections.append("# Athlete's Context for UPCOMING WEEK (Next Week)\n")
            sections.append("**IMPORTANT:** The athlete provided this information about NEXT WEEK (the week you're planning for), NOT the past week.\n")
            sections.append("This describes upcoming constraints, travel, races, and availability for THE WEEK YOU ARE ABOUT TO PLAN.\n\n")
        else:
            sections.append("# Athlete's Context for THE WEEK JUST COMPLETED\n")
            sections.append("**IMPORTANT:** The athlete provided this information about THE PAST WEEK (the week being analyzed), NOT next week.\n")
            sections.append("This describes how they felt, what happened, and any issues during THE WEEK YOU ARE ANALYZING.\n\n")
        
        if user_context.get('schedule_constraints'):
            if is_upcoming_week:
                sections.append("## Schedule & Constraints (FOR NEXT WEEK)")
                sections.append("*These are UPCOMING constraints - schedule workouts AROUND these:*\n")
            else:
                sections.append("## Schedule & Constraints (FROM PAST WEEK)")
                sections.append("*These were constraints during the completed week:*\n")
            sections.append(user_context['schedule_constraints'])
            sections.append("")
        
        if user_context.get('training_focus'):
            if is_upcoming_week:
                sections.append("## Training Focus & Goals (FOR NEXT WEEK)")
                sections.append("*Athlete wants to emphasize this in the upcoming plan:*\n")
            else:
                sections.append("## Training Focus & Goals (FROM PAST WEEK)")
                sections.append("*This was what athlete was focusing on during completed week:*\n")
            sections.append(user_context['training_focus'])
            sections.append("")
        
        if user_context.get('week_feedback'):
            if is_upcoming_week:
                sections.append("## Current Feelings & Readiness (FOR NEXT WEEK)")
                sections.append("*Athlete's current state going into next week:*\n")
            else:
                sections.append("## Week Feedback & Feelings (FROM PAST WEEK)")
                sections.append("*How athlete felt during the completed week:*\n")
            sections.append(user_context['week_feedback'])
            sections.append("")
        
        if is_upcoming_week:
            sections.append("**CRITICAL:** Do NOT schedule hard workouts on days the athlete said they're traveling, racing, or unavailable!")
            sections.append("**CRITICAL:** If athlete mentions 'Friday-Sunday travel', do NOT schedule workouts on Friday, Saturday, OR Sunday!")
        else:
            sections.append("**CRITICAL:** Do NOT confuse this past week's context with next week's planning!")
        
        return "\n".join(sections)
    
    def build_weekly_analysis_prompt(self, context: PromptContext) -> str:
        """
        Build prompt for analyzing the completed week.
        
        Educational note: Task-Specific Prompts
        
        Different tasks need different prompts:
        - Analysis: Focus on observation, pattern recognition
        - Generation: Focus on constraints, output format
        - Validation: Focus on rules, error detection
        
        This is the "analysis" prompt - helps AI understand what happened.
        """
        sections = []
        
        # System prompt
        sections.append(self._build_system_prompt(context.coaching_notes.get('personality', {})))
        sections.append("\n" + "="*80 + "\n")
        
        # RAG knowledge (analysis-focused topics)
        focus_topics = context.focus_topics or {'periodization', 'recovery', 'training'}
        knowledge_chunks = self.rag_loader.retrieve(query_topics=focus_topics, max_tokens=8000)
        sections.append(self.rag_loader.format_for_prompt(knowledge_chunks))
        sections.append("\n" + "="*80 + "\n")
        
        # Athlete context
        sections.append(self._build_athlete_context(context))
        sections.append("\n" + "="*80 + "\n")
        
        # Training context
        sections.append(self._build_training_context(context))
        sections.append("\n" + "="*80 + "\n")
        
        # Coaching history
        sections.append(self._build_coaching_observations(context.coaching_notes))
        sections.append("\n" + "="*80 + "\n")
        
        # User context (weekly input) - FOR ANALYSIS, this is about the PAST week
        if context.user_context:
            # Mark this as past week context for clarity
            user_context_with_type = dict(context.user_context)
            user_context_with_type['context_type'] = 'past_week'
            sections.append(self._build_user_context_section(user_context_with_type))
            sections.append("\n" + "="*80 + "\n")
        
        # Task
        sections.append("""# Your Task: Analyze This Week's Training

Review the athlete's completed week and provide coaching analysis.

## Analysis Framework

Consider these aspects (think step-by-step):

1. **Training Load Assessment**
   - Was the TSS appropriate for current fitness level?
   - How does it compare to recent weeks?
   - Any signs of overreaching or undertraining?

2. **Workout Distribution**
   - Is the mix of workout types appropriate for current training phase?
   - Any missing workout types that should be addressed?
   - Balance between intensity and endurance?

3. **Performance Trends**
   - What patterns emerge from power/HR data?
   - Are metrics improving, stable, or declining?
   - Any concerning trends?

4. **Compliance & Consistency**
   - How well did athlete stick to the plan?
   - Any patterns in missed or modified workouts?

5. **Recovery Indicators**
   - Adequate recovery time between hard efforts?
   - Any signs of accumulated fatigue?

6. **Recommendations for Next Week**
   - Should we maintain, increase, or decrease load?
   - Which workout types to prioritize?
   - Any specific focus areas?

7. **Training Phase Check**
    - Does the current phase still fit the data?
    - If not, suggest the updated phase (Base, Build, Peak, Recovery, Maintenance)

## Output Format

Provide your analysis in this structure:

```
## Week Summary
[2-3 sentence overview of the week]

## Key Observations
- [Observation 1 with supporting data]
- [Observation 2 with supporting data]
- [Observation 3 with supporting data]

## Performance Highlights
- [Positive developments worth celebrating]

## Areas for Attention
- [Things to monitor or adjust]

## Recommendations for Next Week
- [Specific, actionable recommendations]
- [Include rationale based on data]

## Suggested Training Phase
[Base Building | Build | Peak | Recovery | Maintenance]

## Coaching Note
[What should be remembered for future weeks?]
```

Be specific, reference actual numbers from the data, and explain your reasoning.
""")
        
        return "\n".join(sections)
    
    def _build_adaptive_coaching_context(self, context: PromptContext) -> str:
        """
        **NEW: Adaptive Prompting Enhancement**
        
        Build coaching context that adapts based on continuity insights.
        Includes:
        - Recent achievements to celebrate
        - Priority goals to focus on
        - Multi-week patterns detected
        - Sentiment-based tone adjustments
        - Recurring schedule awareness
        
        This makes coaching more personalized and contextually aware.
        """
        sections = []
        
        # Add recent achievements if available
        if context.comprehensive_context and 'achievements' in context.comprehensive_context:
            achievements = context.comprehensive_context['achievements'][-3:]  # Last 3
            if achievements:
                sections.append("## 🏆 Recent Achievements to Acknowledge")
                sections.append("*Celebrate these milestones in your coaching narrative:*\n")
                for ach in achievements:
                    sections.append(f"- **{ach['description']}** ({ach['category']}, Week {ach.get('week_number', '?')})")
                sections.append("")
        
        # Add priority goals for focus
        if context.comprehensive_context and 'goals' in context.comprehensive_context:
            priority_goals = [g for g in context.comprehensive_context['goals'] if g.get('priority', 3) <= 2]
            if priority_goals:
                sections.append("## 🎯 Priority Goals (Focus Training Here)")
                sections.append("*These are the athlete's highest-priority goals - align workouts to support them:*\n")
                for goal in priority_goals:
                    priority_emoji = "🔥" if goal['priority'] == 1 else "⭐"
                    target = f" (Target: {goal.get('target_date', 'ongoing')})" if goal.get('target_date') else ""
                    sections.append(f"- {priority_emoji} **Priority {goal['priority']}:** {goal['description']}{target}")
                    if goal.get('progress_notes'):
                        for note in goal['progress_notes'][-1:]:  # Most recent note
                            sections.append(f"  - _{note}_")
                sections.append("")
        
        # Add multi-week pattern insights if available
        if context.comprehensive_context and 'pattern_analysis' in context.comprehensive_context:
            patterns = context.comprehensive_context['pattern_analysis']
            if patterns.get('patterns_detected'):
                sections.append("## 📊 Multi-Week Trend Analysis")
                sections.append("*Adjust coaching based on these detected patterns:*\n")
                
                if patterns.get('power_trend'):
                    trend = patterns['power_trend']
                    if trend == 'improving':
                        sections.append("- **Power Trend:** ✅ Improving - Continue current training stimulus")
                    elif trend == 'declining':
                        sections.append("- **Power Trend:** ⚠️ Declining - Consider recovery week or reduced intensity")
                    else:
                        sections.append("- **Power Trend:** ➡️ Stable - Can progress volume or intensity")
                
                if patterns.get('recovery_trend'):
                    trend = patterns['recovery_trend']
                    if trend == 'declining':
                        sections.append("- **Recovery Trend:** ⚠️ Declining - Prioritize rest and deload")
                    elif trend == 'strong':
                        sections.append("- **Recovery Trend:** ✅ Strong - Athlete can handle increased load")
                    else:
                        sections.append("- **Recovery Trend:** ➡️ Adequate - Maintain current recovery strategy")
                
                if patterns.get('insights'):
                    sections.append("\n**Key Pattern Insights:**")
                    for insight in patterns['insights'][:3]:  # Top 3 insights
                        sections.append(f"  - {insight}")
                sections.append("")
        
        # Add recurring schedule reminders
        if context.comprehensive_context and 'coaching_continuity' in context.comprehensive_context:
            continuity = context.comprehensive_context['coaching_continuity']
            if continuity:
                last_continuity = continuity[-1]
                if last_continuity.get('recurring_schedule'):
                    sections.append("## 📅 Recurring Schedule (Don't Re-Ask)")
                    sections.append("*Athlete has these standing commitments - work around them:*\n")
                    for day, activity in last_continuity['recurring_schedule'].items():
                        sections.append(f"- **{day}:** {activity}")
                    sections.append("")
        
        if sections:
            return "\n".join(sections)
        return ""
    
    def build_workout_generation_prompt(self, context: PromptContext, 
                                       analysis_output: Optional[str] = None) -> str:
        """
        Build prompt for generating next week's workout plan.
        
        Educational note: Chained Prompts
        
        Complex tasks → Multiple prompts in sequence:
        1. Analyze (understand what happened)
        2. Generate (create plan based on analysis)
        3. Validate (check plan correctness)
        
        Why not one big prompt?
        - Cognitive load (too much to think about at once)
        - Quality (each step focused on one task)
        - Debuggability (see where it breaks)
        
        This is step 2: Generation
        """
        sections = []
        
        # System prompt
        sections.append(self._build_system_prompt(context.coaching_notes.get('personality', {})))
        sections.append("\n" + "="*80 + "\n")
        
        # RAG knowledge (generation-focused topics)
        gen_topics = context.focus_topics or {'intervals', 'periodization', 'json', 'format'}
        knowledge_chunks = self.rag_loader.retrieve(query_topics=gen_topics, max_tokens=6000)
        sections.append(self.rag_loader.format_for_prompt(knowledge_chunks))
        sections.append("\n" + "="*80 + "\n")
        
        # Athlete context
        sections.append(self._build_athlete_context(context))
        sections.append("\n" + "="*80 + "\n")
        
        # NEW: Adaptive coaching context based on continuity insights
        adaptive_context = self._build_adaptive_coaching_context(context)
        if adaptive_context:
            sections.append("# 🎯 ADAPTIVE COACHING CONTEXT\n")
            sections.append("*Use these insights to personalize your coaching approach this week:*\n\n")
            sections.append(adaptive_context)
            sections.append("\n" + "="*80 + "\n")
        
        # Training context
        sections.append(self._build_training_context(context))
        sections.append("\n" + "="*80 + "\n")
        
        if context.training_state:
            from src.utils.coach_context import PROGRESSION_RULES
            sections.append(context.training_state)
            sections.append("\n" + PROGRESSION_RULES)
            sections.append("\n" + "="*80 + "\n")
        elif context.comprehensive_context and context.comprehensive_context.get('weekly_summary'):
            sections.append(self._build_tss_baseline_guidance(context.comprehensive_context['weekly_summary']))
            sections.append("\n" + "="*80 + "\n")
        
        # Include analysis if provided
        if analysis_output:
            sections.append("# Weekly Analysis Results\n")
            sections.append(analysis_output)
            sections.append("\n" + "="*80 + "\n")
        
        # User context (weekly input) - FOR GENERATION, this is about the UPCOMING week
        if context.user_context:
            # Mark this as upcoming week context for clarity
            user_context_with_type = dict(context.user_context)
            user_context_with_type['context_type'] = 'upcoming_week'
            sections.append(self._build_user_context_section(user_context_with_type))
            sections.append("\n" + "="*80 + "\n")
        
        # Constraints
        if context.constraints:
            sections.append("# Athlete Constraints for Next Week\n")
            for key, value in context.constraints.items():
                sections.append(f"- **{key}:** {value}")
            sections.append("\n" + "="*80 + "\n")
        
        # Task
        sections.append("""# Your Task: Generate Next Week's Training Plan

**CRITICAL WEEK STRUCTURE:**
- Training weeks run **MONDAY (Day 1) through SUNDAY (Day 7)**
- Monday is ALWAYS the first day of the week
- Sunday is ALWAYS the last day of the week
- You MUST create exactly 7 days in this order: Mon, Tue, Wed, Thu, Fri, Sat, Sun

Create a 7-day workout plan based on your analysis and the athlete's context.

## Critical Requirements

1. **Week Structure (MANDATORY):**
   - Day 1: Monday (start of week)
   - Day 2: Tuesday
   - Day 3: Wednesday  
   - Day 4: Thursday
   - Day 5: Friday
   - Day 6: Saturday
   - Day 7: Sunday (end of week)

2. **Output must be valid JSON** following the exact schema in the knowledge base
3. **Include FTP value** at top level (current: {ftp}W)
4. **All durations in proper units:**
   - Intervals: SECONDS
   - Workout totals: MINUTES
5. **Use date format:** YYYY-MM-DD (starting Monday)
6. **Progressive structure:** Build through week, lighter on recovery days

## Planning Process (Think Step-by-Step)

1. **Determine Training Phase**
   - Where is athlete in periodization cycle?
   - What should be emphasized this week?

2. **Weekly Load (CRITICAL)**
   - Use the weekly TSS band in "Next Week's Load Target" when present; it is computed
     from fitness (CTL), a safe ramp, the build/recovery cadence and event tapers.
     Plans outside it are rejected. Otherwise use the Multi-Week TSS Baseline section.
   - **DISTRIBUTION:** Spread TSS across 7 days (hard days 70-120 TSS, easy days 20-50 TSS)

3. **Choose and Progress Key Sessions**
   - Follow the progression rules above: 2-3 key sessions that serve the current block,
     each a deliberate step from the last session of that type in the progression table.
   - Vary structure within a type (e.g. 3x15 → 2x22 threshold), not the type week to week.
   - Balance intensity vs volume; include 1-2 easy days minimum.

   **WORKOUT TYPE REFERENCE:**
   - Threshold: Steady 2x15min or 2x20min @ FTP
   - Sweet Spot: 3x12min @ 88-93% FTP (great for building)
   - Over/Unders: 4x8min alternating 95%/105% FTP (race simulation)
   - Tempo: Long 30-60min @ 76-85% FTP
   - VO2max: Classic 5x5min or progressive 4x4min
   - Endurance: Long 2-4 hour Zone 2 (60-74% FTP)
   - Pyramids: 3-5-7-5-3min @ threshold with equal rest

4. **Design Specific Workouts**
   - Interval structure (duration, intensity, rest)
   - Warm-up (15-20min progressive) and cool-down (10-15min)
   - Progressive difficulty through sets (e.g., increasing power or decreasing rest)
   - Include coaching notes explaining workout purpose

5. **Placement**
   - Placing key sessions on different days week to week is fine when the schedule calls
     for it; keep at least 48h between hard days.

6. **Sequence Workouts (ATHLETE SCHEDULE FIRST!)**
   - **FIRST:** Review athlete's constraints (travel, races, work conflicts) in \"Athlete's Context\" section
   - **THEN:** Place hard days on AVAILABLE days with 48hr spacing
   - If athlete says \"Friday morning flight\" → Friday = NO hard workout
   - If athlete says \"traveling Fri-Sun\" → Friday, Saturday, Sunday = light/rest only
   - If no constraints: Hard days need 48hr between (e.g., Mon/Wed/Fri or Tue/Thu/Sat)
   - Recovery positioned strategically (day before/after hard efforts)

7. **Add Context**
   - Workout descriptions
   - Week focus notes
   - Special considerations

## Output Format

Return ONLY valid JSON (no markdown code blocks, no extra text).

The JSON must validate against the schema in the knowledge base.

**CRITICAL: Use these specific values for the next week:**
- weekNumber: {week_number}
- startDate: "{start_date}"

Example structure (but adapt to athlete's needs):
```json
{{
  "weekNumber": {week_number},
  "startDate": "{start_date}",
  "ftp": {ftp},
  "plannedTSS": {{
    "min": 400,
    "max": 500
  }},
  "notes": {{
    "weekFocus": "Progressive base building with threshold maintenance",
    "specialConsiderations": "Monitor recovery, adjust as needed"
  }},
  "days": [
    ... (7 day objects with workouts)
  ]
}}
```

Remember: Quality over quantity. Each workout should have clear purpose and proper progression.
""".format(
    ftp=context.athlete_profile.get('current_ftp', 300),
    week_number=(context.user_context or {}).get('next_week_number', 52),
    start_date=(context.user_context or {}).get('next_week_start_date', '2025-11-18')
))
        
        return "\n".join(sections)
    
    def _build_prior_sessions_context(self, prior_sessions: list) -> str:
        """
        Format prior chat session transcripts so the coach has memory of what
        the athlete mentioned in recent weeks (events, goals, schedule, concerns).
        Only assistant + user turns are included — system overhead is stripped.
        """
        sections = ["# Prior Coaching Conversations\n"]
        sections.append(
            "The following are transcripts of recent coaching sessions. "
            "Use them to avoid re-asking questions the athlete has already answered, "
            "and to maintain continuity on topics like upcoming events, stated goals, "
            "schedule constraints, and ongoing themes.\n"
        )
        for session in reversed(prior_sessions):  # chronological order
            week = session.get('week_start_date', 'unknown')
            week_num = session.get('plan_week_number')
            header = f"## Week starting {week}" + (f" (Week {week_num})" if week_num else "")
            sections.append(header)
            messages = session.get('messages', [])
            if not messages:
                sections.append("*(no transcript)*\n")
                continue
            turn_lines = []
            for m in messages:
                role = m.get('role', 'user')
                content = m.get('content', '').strip()
                if not content:
                    continue
                label = "Athlete" if role == "user" else "Coach"
                # Truncate very long turns to keep token budget reasonable
                if len(content) > 600:
                    content = content[:600] + "…"
                turn_lines.append(f"**{label}:** {content}")
            sections.append("\n".join(turn_lines))
            sections.append("")
        return "\n".join(sections)

    def build_chat_system_prompt(self, weekly_summary: Dict,
                                  comprehensive_context: Optional[Dict],
                                  coaching_notes: Dict,
                                  prior_sessions: Optional[list] = None,
                                  training_state: Optional[str] = None,
                                  tools_enabled: bool = False) -> str:
        """
        Build the one-shot system prompt for the interactive chat coach session.

        The AI receives full DB context upfront and then converses naturally,
        asking clarifying questions (≤3 turns) before emitting the sentinel
        token READY_TO_GENERATE when it has enough information.
        """
        context = PromptContext(
            athlete_profile=coaching_notes.get('athlete_profile', {}),
            coaching_notes=coaching_notes,
            weekly_summary=weekly_summary,
            comprehensive_context=comprehensive_context or {},
        )

        sections = []
        sections.append(self._build_system_prompt(coaching_notes.get('personality', {})))
        sections.append("\n" + "=" * 80 + "\n")
        sections.append(self._build_athlete_context(context))
        sections.append("\n" + "=" * 80 + "\n")

        # Goals & event timeline — injected here so the coach holds event context
        # throughout the entire conversation, not just at plan generation time
        goals = coaching_notes.get('goals', [])
        if goals:
            sections.append(self._build_goals_context(goals))
            sections.append("\n" + "=" * 80 + "\n")

        sections.append(self._build_training_context(context))
        sections.append("\n" + "=" * 80 + "\n")
        sections.append(self._build_coaching_observations(coaching_notes))
        sections.append("\n" + "=" * 80 + "\n")

        if training_state:
            # Computed load/progression/readiness supersedes the simple TSS baseline.
            sections.append(training_state)
            sections.append("\n" + "=" * 80 + "\n")
        else:
            # Producer key is 'weekly_summary' (ai_database_queries.get_comprehensive_context).
            recent_weeks = comprehensive_context.get('weekly_summary', []) if comprehensive_context else []
            if recent_weeks:
                sections.append(self._build_tss_baseline_guidance(recent_weeks))
                sections.append("\n" + "=" * 80 + "\n")

        # Inject prior chat transcripts so the coach remembers what the athlete said
        if prior_sessions:
            sections.append(self._build_prior_sessions_context(prior_sessions))
            sections.append("\n" + "=" * 80 + "\n")

        sections.append("""# Interactive Chat Coaching Instructions

You are now in an interactive chat session with the athlete.  Your goal is to
gather enough context to build next week's training plan.

## Conversation Flow

1. **Greet & Analyse** – Open by summarising the completed week's highlights
   in 2-3 sentences (TSS, key workouts, trends you noticed).

2. **Ask Clarifying Questions** – You may ask UP TO 3 rounds of questions to
   understand:
   - How the athlete felt / any soreness or fatigue
   - Upcoming week schedule constraints (races, travel, work)
   - Any goals or focus they want emphasised

3. **Signal readiness** – Once you have enough context (or after 3 clarifying
   rounds), end your message with the exact token on its own line:

   READY_TO_GENERATE

   Do NOT include this token until you genuinely have enough context.

## Style Guidelines
- Be warm, concise, and data-driven
- Reference specific numbers from the athlete's data
- Ask at most 2-3 questions per turn (not a wall of questions)
- Keep each message under 200 words unless the athlete asks for detail
- Do NOT start generating the plan until you emit READY_TO_GENERATE
""")
        if tools_enabled:
            from src.utils.coach_context import TOOL_INSTRUCTIONS
            sections.append(TOOL_INSTRUCTIONS)

        return "\n".join(sections)

    def build_surgical_edit_prompt(self, current_plan_json: Dict, feedback: str) -> str:
        """
        Build a prompt asking the AI to return only the modified day(s) as a
        JSON delta: {"modified_days": [<day objects matching existing schema>]}

        The caller merges this delta into the stored plan by dayNumber.
        """
        import json
        plan_str = json.dumps(current_plan_json, indent=2)

        return f"""You are a cycling coach reviewing an athlete's training plan.
The athlete has provided feedback about specific days they want adjusted.

# Current Plan
```json
{plan_str}
```

# Athlete Feedback
{feedback}

# Your Task
Apply the athlete's requested changes and return ONLY the affected day objects.

## CRITICAL Output Rules
- Return EXACTLY this JSON format, nothing else:
  {{"modified_days": [<array of complete day objects that changed>]}}
- Each day object must match the EXACT schema from the current plan above
  (same keys: dayNumber, date, workouts array, etc.)
- Only include days that actually changed
- Do NOT include commentary, markdown fences, or any text outside the JSON
- Preserve all unchanged workouts within a modified day exactly as-is
- If a day becomes a rest day, set "workouts" to []
"""

    def estimate_prompt_tokens(self, prompt: str) -> int:
        """Estimate tokens in a prompt."""
        return len(prompt) // 4


# Test and demonstrate
if __name__ == "__main__":
    print("🎯 AI Coach Prompt Engineering - Educational Demo\n")
    print("=" * 80)
    
    # Create sample context
    sample_profile = {
        'name': 'Athlete',  # Loaded from coaching_notes.json
        'current_ftp': 300,
        'starting_ftp': 200,
        'primary_goals': [
            'Complete 50-100 mile gravel rides',
            'Improve FTP to 320W+',
            'Build sustainable endurance'
        ],
        'seasonal_preferences': {
            'winter': 'XC skiing, indoor training',
            'spring': 'Gravel racing, trail running',
            'summer': 'Long endurance events',
            'fall': 'Gravel racing, cyclocross'
        }
    }
    
    sample_notes = {
        'personality': {
            'style': 'data-driven, encouraging, scientific',
            'voice': 'professional yet approachable',
            'communication_preferences': [
                "Explain the 'why' behind recommendations",
                "Use data to support decisions",
                "Acknowledge progress"
            ]
        },
        'current_training_phase': 'Base Building',
        'next_week_focus': 'Progressive endurance development',
        'observations': [
            {
                'week_number': 1,
                'date': '2025-11-11',
                'observation': 'Good consistency, power trends improving',
                'focus_areas': ['endurance', 'recovery'],
                'athlete_response': 'Felt strong on endurance rides'
            }
        ]
    }
    
    sample_weekly = {
        'start_date': '2025-11-04',
        'end_date': '2025-11-10',
        'total_tss': 425,
        'total_training_hours': 8.5,
        'sessions_completed': 6
    }
    
    sample_comprehensive = {
        'workout_compliance': {
            'overall_compliance_pct': 75.0,
            'total_completed': 6,
            'total_planned': 8
        },
        'workout_type_distribution': {
            'weeks_analyzed': 4,
            'distribution': {'Recovery': 6, 'Endurance': 4, 'Threshold': 2},
            'distribution_pct': {'Recovery': 50.0, 'Endurance': 33.3, 'Threshold': 16.7}
        },
        'power_trends': {
            'latest_avg_power': 205,
            'trend': 'improving'
        }
    }
    
    context = PromptContext(
        athlete_profile=sample_profile,
        coaching_notes=sample_notes,
        weekly_summary=sample_weekly,
        comprehensive_context=sample_comprehensive
    )
    
    print("1️⃣ INITIALIZING PROMPT SYSTEM")
    print("=" * 80)
    prompts = AICoachPrompts()
    print("✅ Loaded RAG context and prompt templates\n")
    
    print("2️⃣ BUILDING WEEKLY ANALYSIS PROMPT")
    print("=" * 80)
    analysis_prompt = prompts.build_weekly_analysis_prompt(context)
    token_count = prompts.estimate_prompt_tokens(analysis_prompt)
    print(f"📊 Prompt size: {len(analysis_prompt):,} characters (~{token_count:,} tokens)\n")
    
    print("Preview (first 1000 chars):")
    print("-" * 80)
    print(analysis_prompt[:1000])
    print("\n... [truncated] ...\n")
    
    print("3️⃣ PROMPT STRUCTURE BREAKDOWN")
    print("=" * 80)
    sections = analysis_prompt.split("=" * 80)
    for i, section in enumerate(sections[:6], 1):
        lines = section.strip().split('\n')
        first_line = lines[0] if lines else ""
        section_tokens = prompts.estimate_prompt_tokens(section)
        print(f"Section {i}: {first_line[:50]:50s} ~{section_tokens:5,} tokens")
    
    print(f"\n4️⃣ WORKOUT GENERATION PROMPT")
    print("=" * 80)
    gen_prompt = prompts.build_workout_generation_prompt(context)
    gen_tokens = prompts.estimate_prompt_tokens(gen_prompt)
    print(f"📊 Prompt size: {len(gen_prompt):,} characters (~{gen_tokens:,} tokens)\n")
    
    print("✅ Prompt system ready for AI coaching!")
    print("\n💡 Educational Summary:")
    print("-" * 80)
    print("✓ Modular prompt construction (system + knowledge + data + task)")
    print("✓ RAG integration (only ~8-12K tokens of relevant knowledge)")
    print("✓ Structured output requirements (JSON schema)")
    print("✓ Step-by-step reasoning (chain-of-thought)")
    print("✓ Token budgeting (analysis: ~{:,}, generation: ~{:,})".format(token_count, gen_tokens))
