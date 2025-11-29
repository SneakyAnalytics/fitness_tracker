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
        
        sections.append(f"**Training Phase:** {context.coaching_notes.get('current_training_phase', 'Not specified')}")
        
        # Goals
        if profile.get('primary_goals'):
            sections.append("\n## Primary Goals")
            sections.append(self._format_list(profile['primary_goals']))
        
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
                    if analysis_data:
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
                        efforts_str = ", ".join([f"{dur}: {int(power)}W" for dur, power in peak_efforts.items() if power])
                        if efforts_str:
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
            sections.append("\n## Workout-Specific Trends (Last 12 Weeks)")
            for wtype, analysis in comp_ctx['workout_type_progressions'].items():
                if analysis.get('count', 0) > 0:
                    sections.append(f"\n### {wtype}")
                    sections.append(f"- **Count:** {analysis['count']} workouts")
                    
                    if analysis.get('averages'):
                        for metric, value in list(analysis['averages'].items())[:3]:
                            trend = analysis['trends'].get(metric, 'stable')
                            trend_emoji = {'improving': '📈', 'declining': '📉', 'stable': '➡️'}.get(trend, '')
                            sections.append(f"- **{metric}:** {value:.1f} [{trend} {trend_emoji}]")
        
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
            sections.append("## Last Week's Continuity Notes")
            sections.append("*Your observations and priorities from the most recent coaching session:*\n")
            
            # Get most recent continuity
            last_week = continuity[-1] if continuity else None
            if last_week:
                if last_week.get('key_observations'):
                    sections.append("**Key Observations:**")
                    for obs in last_week['key_observations']:
                        sections.append(f"- {obs}")
                    sections.append("")
                
                if last_week.get('progression'):
                    sections.append("**Progression Notes:**")
                    for prog in last_week['progression']:
                        sections.append(f"- {prog}")
                    sections.append("")
                
                if last_week.get('monitor'):
                    sections.append("**Areas to Monitor:**")
                    for area in last_week['monitor']:
                        sections.append(f"- {area}")
                    sections.append("")
                
                if last_week.get('next_priorities'):
                    sections.append("**Priorities for This Week:**")
                    for priority in last_week['next_priorities']:
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
        
        # Current focus
        if coaching_notes.get('next_week_focus'):
            sections.append(f"\n## Planned Next Week Focus")
            sections.append(coaching_notes['next_week_focus'])
        
        return "\n".join(sections)
    
    def _build_user_context_section(self, user_context: Dict) -> str:
        """
        Format user-provided weekly context (schedule, focus, feedback).
        
        This is the interactive element where users provide weekly input:
        - Schedule constraints (races, work conflicts, heat chamber, etc.)
        - Training focus for upcoming week
        - Feedback on how they're feeling
        """
        sections = []
        sections.append("# Athlete's Weekly Context\n")
        sections.append("The athlete has provided the following context for this week:\n")
        
        if user_context.get('schedule_constraints'):
            sections.append("## Schedule & Constraints")
            sections.append(user_context['schedule_constraints'])
            sections.append("")
        
        if user_context.get('training_focus'):
            sections.append("## Training Focus & Goals")
            sections.append(user_context['training_focus'])
            sections.append("")
        
        if user_context.get('week_feedback'):
            sections.append("## Week Feedback & Feelings")
            sections.append(user_context['week_feedback'])
            sections.append("")
        
        sections.append("**Important:** Factor this athlete input into your analysis and recommendations.")
        
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
        
        # User context (weekly input)
        if context.user_context:
            sections.append(self._build_user_context_section(context.user_context))
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

## Coaching Note
[What should be remembered for future weeks?]
```

Be specific, reference actual numbers from the data, and explain your reasoning.
""")
        
        return "\n".join(sections)
    
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
        knowledge_chunks = self.rag_loader.retrieve(query_topics=gen_topics, max_tokens=12000)
        sections.append(self.rag_loader.format_for_prompt(knowledge_chunks))
        sections.append("\n" + "="*80 + "\n")
        
        # Athlete context
        sections.append(self._build_athlete_context(context))
        sections.append("\n" + "="*80 + "\n")
        
        # Training context
        sections.append(self._build_training_context(context))
        sections.append("\n" + "="*80 + "\n")
        
        # Include analysis if provided
        if analysis_output:
            sections.append("# Weekly Analysis Results\n")
            sections.append(analysis_output)
            sections.append("\n" + "="*80 + "\n")
        
        # User context (weekly input)
        if context.user_context:
            sections.append(self._build_user_context_section(context.user_context))
            sections.append("\n" + "="*80 + "\n")
        
        # Constraints
        if context.constraints:
            sections.append("# Athlete Constraints for Next Week\n")
            for key, value in context.constraints.items():
                sections.append(f"- **{key}:** {value}")
            sections.append("\n" + "="*80 + "\n")
        
        # Task
        sections.append("""# Your Task: Generate Next Week's Training Plan

Create a 7-day workout plan based on your analysis and the athlete's context.

## Critical Requirements

1. **Output must be valid JSON** following the exact schema in the knowledge base
2. **Include FTP value** at top level (current: {ftp}W)
3. **All durations in proper units:**
   - Intervals: SECONDS
   - Workout totals: MINUTES
4. **Use date format:** YYYY-MM-DD (starting Monday)
5. **Progressive structure:** Build through week, lighter on recovery days

## Planning Process (Think Step-by-Step)

1. **Determine Training Phase**
   - Where is athlete in periodization cycle?
   - What should be emphasized this week?

2. **Calculate Weekly Load**
   - Target TSS range (consider last week's load ± 10-20%)
   - Distribution across 7 days

3. **Select Workout Types**
   - Which energy systems to target?
   - Balance intensity vs volume
   - Include appropriate recovery

4. **Design Specific Workouts**
   - Interval structure (duration, intensity, rest)
   - Warm-up and cool-down
   - Progressive difficulty through sets

5. **Sequence Workouts**
   - Hard days properly spaced
   - Recovery positioned strategically
   - Consider weekly flow

6. **Add Context**
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
