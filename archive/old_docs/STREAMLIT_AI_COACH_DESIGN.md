# AI Coach Streamlit Interface Design

## Context Input & Weekly Coaching Flow

Based on requirements:

1. ✅ Rich weekly summary data already exists (generate_weekly_summary)
2. ❌ Need interactive context input each week (not hardcoded JSON)
3. ❌ Need cross-training classification
4. ❌ Need AI feedback loop (continuity)

---

## Phase 1: Enhanced Data Flow (Fix What AI Sees)

### 1.1 Use REAL Weekly Summary Data

**Current:** Test used minimal mock data

```python
sample_summary = {
    'total_tss': 425.0,
    'total_training_hours': 8.5,
    'sessions_completed': 6,
    'workout_types': ['Bike'],
    'qualitative_feedback': []  # EMPTY!
}
```

**Available (from generate_weekly_summary):**

```python
{
    'total_tss': 425.0,
    'total_training_hours': 8.5,
    'sessions_completed': 21,
    'workout_types': ['Bike', 'Run', 'Other'],
    'qualitative_feedback': [  # FULL workout details!
        {
            'day': '2025-11-10',
            'type': 'Bike',
            'title': 'Recovery Spin',
            'workout_data': {
                'metrics': {'actual_tss': 24.79, 'actual_duration': 45.15, 'rpe': null},
                'power_data': {'average': 171, 'max': 191, 'if': 0.58, 'zones': {...}},
                'heart_rate_data': {'average_hr': 120, 'max_hr': 131, 'zones': {...}}
            },
            'feedback': {'athlete_comments': null}
        },
        {
            'day': '2025-11-08',
            'type': 'Run',
            'title': 'Morning Easy Run',
            'workout_data': {
                'metrics': {'actual_tss': 35, 'actual_duration': 45},
                'heart_rate_data': {'average_hr': 145, 'max_hr': 162, 'zones': {...}},
                'power_data': null
            }
        },
        # ... 19 more workouts with full details
    ],
    'daily_energy': {'2025-11-10': 3.5, '2025-11-09': 4.2, ...},
    'avg_daily_energy': 3.8,
    'daily_sleep_quality': {'2025-11-10': {'sleep_quality_score': 4.2}, ...},
    'avg_sleep_quality': 4.0,
    'weekly_plan': {...},
    'proposed_workouts': [...]
}
```

**Action:** Update `ai_coach_engine.py` test to use real database query instead of mock

### 1.2 Cross-Training Classification Enhancement

**Problem:** workout_type_analyzer only classifies Bike workouts

**Solution:** Extend to handle all activity types based on what's in the database

```python
# In workout_type_analyzer.py - add new classification methods

def classify_run_workout(self, title: str, avg_hr: Optional[float], max_hr: Optional[float],
                        duration_minutes: float) -> str:
    """Classify running workouts based on HR zones and duration"""

    RUN_PATTERNS = {
        'Easy Run': [r'easy', r'recovery', r'base', r'z1', r'z2', r'jog'],
        'Tempo Run': [r'tempo', r'threshold', r'z3', r'steady'],
        'Long Run': [],  # Duration-based (>75 min)
        'Intervals': [r'interval', r'vo2', r'z4', r'z5', r'speed', r'track'],
        'Progression Run': [r'progression', r'negative split'],
    }

    # Pattern matching on title
    title_lower = title.lower()
    for run_type, patterns in RUN_PATTERNS.items():
        if any(re.search(pattern, title_lower) for pattern in patterns):
            return run_type

    # Duration-based classification
    if duration_minutes > 75:
        return 'Long Run'

    # HR-based classification (if available)
    if avg_hr:
        # Would need athlete's HR zones, similar to power zones
        # For now, simple heuristic
        pass

    return 'Easy Run'  # Default

def classify_strength_workout(self, title: str, performance_data: Optional[Dict]) -> str:
    """Classify strength training workouts"""

    STRENGTH_PATTERNS = {
        'Upper Body': [r'upper', r'chest', r'back', r'shoulder', r'arm', r'pull', r'push'],
        'Lower Body': [r'lower', r'leg', r'squat', r'deadlift', r'glute'],
        'Full Body': [r'full body', r'total body', r'circuit'],
        'Core': [r'core', r'ab', r'plank', r'stability'],
    }

    title_lower = title.lower()
    for strength_type, patterns in STRENGTH_PATTERNS.items():
        if any(re.search(pattern, title_lower) for pattern in patterns):
            return strength_type

    return 'Full Body'  # Default

def classify_mobility_workout(self, title: str) -> str:
    """Classify mobility/flexibility workouts"""

    MOBILITY_PATTERNS = {
        'Yoga': [r'yoga', r'vinyasa', r'flow'],
        'Stretching': [r'stretch', r'flexibility', r'foam roll'],
        'Recovery': [r'recovery', r'restorative', r'active recovery'],
    }

    title_lower = title.lower()
    for mobility_type, patterns in MOBILITY_PATTERNS.items():
        if any(re.search(pattern, title_lower) for pattern in patterns):
            return mobility_type

    return 'Stretching'  # Default

def classify_workout(self, workout: Dict) -> str:
    """Universal workout classifier - handles all activity types"""

    workout_type = workout.get('type', '').lower()
    title = workout.get('title', '')

    if workout_type == 'bike':
        # Existing bike classification
        power_data = workout.get('workout_data', {}).get('power_data', {})
        if_value = power_data.get('intensity_factor')
        return self.classify_bike_workout(title, if_value)

    elif workout_type == 'run':
        hr_data = workout.get('workout_data', {}).get('heart_rate_data', {})
        avg_hr = hr_data.get('average_hr')
        max_hr = hr_data.get('max_hr')
        duration = workout.get('workout_data', {}).get('metrics', {}).get('actual_duration', 0)
        return self.classify_run_workout(title, avg_hr, max_hr, duration)

    elif workout_type in ['strength', 'other']:
        performance_data = workout.get('workout_data', {}).get('performance_data')
        # Check if it's yoga/mobility based on title
        if any(kw in title.lower() for kw in ['yoga', 'stretch', 'mobility']):
            return self.classify_mobility_workout(title)
        else:
            return self.classify_strength_workout(title, performance_data)

    return 'Unclassified'
```

**Action:** Extend workout_type_analyzer.py to handle Run, Strength, Mobility

---

## Phase 2: Streamlit Interface Design

### UI Flow (AI Coach Tab)

```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 AI Coach - Weekly Training Plan                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Step 1: Select Week                                        │
│ ┌───────────────────────────────────────────────────┐     │
│ │ Start Date: [2025-11-04] End Date: [2025-11-10] │     │
│ │ [Load Week Summary]                               │     │
│ └───────────────────────────────────────────────────┘     │
│                                                             │
│ Step 2: Weekly Context (Optional but Recommended)          │
│ ┌───────────────────────────────────────────────────┐     │
│ │ 📅 This Week's Schedule/Constraints:              │     │
│ │ ┌─────────────────────────────────────────────┐   │     │
│ │ │ Tuesday: Zwift racing league (7-8:30pm)    │   │     │
│ │ │ Thursday: Heat chamber session (no hard    │   │     │
│ │ │           training after)                  │   │     │
│ │ │ Saturday: Available for long ride          │   │     │
│ │ └─────────────────────────────────────────────┘   │     │
│ │                                                   │     │
│ │ 🎯 Current Training Focus/Goals:                 │     │
│ │ ┌─────────────────────────────────────────────┐   │     │
│ │ │ Building base for Oregon gravel events     │   │     │
│ │ │ Maintaining XC ski fitness                 │   │     │
│ │ └─────────────────────────────────────────────┘   │     │
│ │                                                   │     │
│ │ 💭 How did this past week feel?                  │     │
│ │ ┌─────────────────────────────────────────────┐   │     │
│ │ │ Felt strong on Tuesday race, a bit tired  │   │     │
│ │ │ after. Recovery runs felt good. Ready for │   │     │
│ │ │ more volume.                               │   │     │
│ │ └─────────────────────────────────────────────┘   │     │
│ └───────────────────────────────────────────────────┘     │
│                                                             │
│ [🚀 Generate AI Coaching Plan]                             │
│                                                             │
│ ─────────────────────────────────────────────────────────  │
│                                                             │
│ Step 3: Review AI Analysis                                 │
│ ┌───────────────────────────────────────────────────┐     │
│ │ ## Week Summary                                   │     │
│ │ Great week with 425 TSS over 8.5 hours across 21 │     │
│ │ workouts. Strong cross-training mix...            │     │
│ │                                                   │     │
│ │ ## Training Distribution                          │     │
│ │ - Bike: 15 workouts (6 recovery, 2 threshold...)  │     │
│ │ - Run: 5 workouts (4 easy, 1 tempo)              │     │
│ │ - Strength: 1 workout (full body)                │     │
│ │                                                   │     │
│ │ ## Key Observations                               │     │
│ │ Tuesday Zwift races providing consistent high-    │     │
│ │ intensity stimulus. Running volume appropriate... │     │
│ └───────────────────────────────────────────────────┘     │
│                                                             │
│ Step 4: Review Proposed Plan                               │
│ ┌───────────────────────────────────────────────────┐     │
│ │ Week 52 Plan (Nov 11-17, 2025)                   │     │
│ │ Target TSS: 450-480 | FTP: 300W                  │     │
│ │                                                   │     │
│ │ Monday:    Yoga & Mobility (30 min)              │     │
│ │ Tuesday:   Sweet Spot Intervals (75 min, 85 TSS) │     │
│ │ Wednesday: Easy Run (45 min, Z2)                 │     │
│ │ Thursday:  Recovery Spin (45 min, 30 TSS)        │     │
│ │ Friday:    Rest / Stretching                     │     │
│ │ Saturday:  Long Endurance Ride (3hr, 180 TSS)    │     │
│ │ Sunday:    Easy Run (60 min, Z2)                 │     │
│ └───────────────────────────────────────────────────┘     │
│                                                             │
│ [✅ Approve & Generate Zwift Files] [✏️ Edit Plan]        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key UI Components

**1. Context Input (Text Areas)**

- **Schedule/Constraints** (multiline text)

  - Freeform: "Tuesday race, Thursday heat chamber, Saturday free for long ride"
  - Saved with each coaching session
  - Available in next week's prompt as "last week's constraints"

- **Training Focus** (multiline text)
  - Freeform: "Building base, maintaining ski fitness, upcoming gravel event in March"
  - Updates coaching_notes.json `current_focus` field
- **Week Feedback** (multiline text)
  - Freeform: "Felt strong Tuesday, tired Wednesday, ready for more"
  - Sent directly to AI as athlete input
  - NOT saved long-term (weekly context only)

**2. Data Sources Combined in Prompt**

```python
# In ai_coach_engine.py - enhance analyze_week()

def analyze_week(self, weekly_summary: Dict, user_context: Optional[Dict] = None):
    """
    Analyze week with FULL data integration

    Args:
        weekly_summary: FULL output from database.generate_weekly_summary()
        user_context: {
            'schedule_constraints': "Tuesday race, Thursday chamber...",
            'training_focus': "Building base for gravel...",
            'week_feedback': "Felt strong on Tuesday..."
        }
    """

    # Get comprehensive context (existing)
    comprehensive_context = self.db_queries.get_comprehensive_context(weeks_back=4)

    # Enhance with classified workouts from weekly_summary
    classified_workouts = self._classify_all_workouts(
        weekly_summary['qualitative_feedback']
    )

    # Build enhanced context for prompt
    context = PromptContext(
        athlete_profile=athlete_profile,
        coaching_notes=coaching_notes,
        weekly_summary=weekly_summary,  # FULL summary with all workouts
        comprehensive_context=comprehensive_context,
        classified_workouts=classified_workouts,  # NEW: Cross-training classified
        user_context=user_context,  # NEW: This week's context from UI
        focus_topics={'periodization', 'recovery', 'training', 'cross-training'}
    )
```

**3. Prompt Enhancement**

```python
# In ai_prompts.py - update build_weekly_analysis_prompt()

def build_weekly_analysis_prompt(self, context: PromptContext) -> str:
    """Build analysis prompt with user context"""

    # ... existing system, RAG, athlete, training sections ...

    # NEW: Add user-provided context section
    user_context_section = ""
    if context.user_context:
        user_context_section = f"""

## Athlete's Context for This Week

**Schedule & Constraints:**
{context.user_context.get('schedule_constraints', 'None provided')}

**Current Training Focus:**
{context.user_context.get('training_focus', 'None provided')}

**How Last Week Felt (Athlete's Words):**
{context.user_context.get('week_feedback', 'No feedback provided')}

"""

    # Add classified workout breakdown
    workout_breakdown = self._format_classified_workouts(context.classified_workouts)

    prompt = f"""
{system_prompt}

{rag_knowledge}

{athlete_context}

{training_context}

{workout_breakdown}  # NEW: Detailed breakdown by type

{user_context_section}  # NEW: User input

{coaching_observations}

{task_instructions}
"""

    return prompt
```

---

## Phase 3: AI Feedback Loop (Continuity)

### Save AI Insights Back to coaching_notes.json

```python
# After successful coaching session:

def _update_coaching_notes(self, analysis: str, workout_plan: Dict):
    """Extract and save AI insights for next week"""

    # Parse key observations from analysis
    # (Could ask AI to return structured coaching_update in JSON)

    new_observation = {
        'date': datetime.now().isoformat(),
        'week_number': workout_plan['weekNumber'],
        'observation': self._extract_key_observation(analysis),
        'focus_areas': self._extract_focus_areas(analysis),
        'athlete_response': 'To be updated next week'
    }

    # Update coaching notes
    self.coaching_notes.add_observation(new_observation)
    self.coaching_notes.save()
```

Or better - ask AI to provide structured update:

```python
# In workout generation prompt, add output requirement:

"""
In addition to the JSON workout plan, provide a coaching_continuity_note:

{
  "workoutPlan": { ... },
  "coaching_continuity": {
    "key_observations": "Athlete responding well to Tuesday races...",
    "areas_to_monitor": ["recovery after heat chamber", "TSS progression"],
    "next_week_priorities": ["maintain Z2 volume", "careful with post-chamber intensity"],
    "schedule_notes": "Tuesday races are working well, continue this pattern"
  }
}
"""
```

---

## Implementation Order

### Phase 3.5: Context Enhancements (3-4 hours)

1. ✅ Update ai_coach_engine test to use **real** generate_weekly_summary() data
2. ✅ Extend workout_type_analyzer for Run, Strength, Mobility classification
3. ✅ Add user_context parameter to analyze_week() and generate_workout_plan()
4. ✅ Update prompts to include classified workouts + user context
5. ✅ Add AI feedback loop (save coaching_continuity back to coaching_notes)

### Phase 4: Streamlit UI (2-3 hours)

1. ✅ Create AI Coach tab in streamlit_app.py
2. ✅ Add week selector + load summary
3. ✅ Add three text input areas (constraints, focus, feedback)
4. ✅ Connect to ai_coach_engine with full context
5. ✅ Display analysis + proposed plan
6. ✅ Approve button → trigger Zwift file generation
7. ✅ Save session (analysis, plan, context, continuity notes)

---

## Benefits of This Approach

### ✅ Interactive Context

- No hardcoded JSON
- Natural text input each week
- Evolves with your schedule

### ✅ Rich Data Integration

- ALL workout details (power, HR, zones, TSS, duration)
- Cross-training properly classified
- Sleep quality, energy levels
- Performance data for strength

### ✅ AI Continuity

- AI learns what works over time
- References previous week's context
- Builds coaching relationship

### ✅ Flexible & Adaptive

- Works for varying schedules (races, travel, chamber sessions)
- Adapts to changing goals (base → build → peak)
- Handles multi-sport training

---

## Example Prompt to AI (After Enhancements)

```
You are an expert endurance coach working with Jake Robinson...

[RAG Knowledge: 12K tokens of cycling science]

## Athlete Profile
Name: Jake Robinson
Current FTP: 300W (up from 200W baseline)
Goals: 50-100 mile Oregon gravel events, maintain multi-sport fitness
...

## Last Week's Training (Nov 4-10, 2025)

Total: 425 TSS, 8.5 hours, 21 workouts

**Bike Workouts (15 total):**
- Recovery: 6 workouts (avg 171W, 24-30 TSS each, HR 120-130 bpm)
- Threshold: 2 workouts (avg 265W, 85 TSS, HR 155-165 bpm)
- Endurance: 2 workouts (avg 205W, 65 TSS, HR 135-145 bpm)
- Race/Event: 3 workouts (including Tuesday Zwift race - 285W, 110 TSS)
- VO2max: 1 workout (290W, 95 TSS)
- Tempo: 1 workout (240W, 70 TSS)

**Run Workouts (5 total):**
- Easy Run: 4 workouts (45-60min, avg HR 145 bpm, Z2, 35-45 TSS each)
- Tempo Run: 1 workout (50min, avg HR 162 bpm, Z3, 55 TSS)

**Other Workouts (1 total):**
- Full Body Strength: 1 workout (45min, 6 exercises, 3 sets each)

**Recovery Metrics:**
- Sleep quality: 4.0/5.0 average (7.2 hrs/night, good deep sleep)
- Daily energy: 3.8/5.0 average (consistent energy levels)

## Athlete's Context for This Week

**Schedule & Constraints:**
Tuesday night: Zwift racing league (7-8:30pm, fixed commitment)
Thursday: Heat chamber research session (limit training that day + Friday)
Saturday: Free for long ride

**Current Training Focus:**
Building aerobic base for Oregon gravel season
Maintaining XC ski fitness (winter approaching)
Continue FTP development toward 320W target

**How Last Week Felt:**
Felt really strong during Tuesday's Zwift race - power was there and legs felt
fresh. A bit tired Wednesday but recovered well. Thursday's easy run felt smooth.
Ready to increase volume slightly.

## Analysis Task
[Provide detailed analysis considering multi-sport training, Tuesday race pattern,
upcoming heat chamber constraint, athlete feedback...]
```

This gives the AI **complete context** to provide truly personalized coaching!
