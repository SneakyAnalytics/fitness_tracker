# AI Coach Enhancement Plan - Cross-Training & Context

## Issues Identified (Nov 13, 2025)

### 1. Cross-Training Not Properly Categorized ❌

**Problem:**

- Running (5 workouts), Mobility (2 workouts) showing as "Unclassified"
- No heart rate data being surfaced for runs
- Strength, XC skiing, hiking not being recognized

**Current State:**

- `workout_type_analyzer.py` only classifies BIKE workouts
- Run/Other workouts fall through as "Unclassified"
- AI incorrectly suggests "need better categorization"

**Solution:**

- [ ] Extend `workout_type_analyzer.py` to handle:
  - **Run**: Easy, Tempo, Long Run, Intervals (use HR zones + pace if available)
  - **Strength**: Upper, Lower, Full Body, Core
  - **Mobility**: Yoga, Stretching, Recovery
  - **XC Ski**: Classic, Skate, Intervals
  - **Hike**: Easy, Moderate, Strenuous
- [ ] Add HR-based classification for cardio activities
- [ ] Include this in comprehensive context sent to AI

### 2. Recurring Weekly Commitments Not Tracked ❌

**Problem:**

- Tuesday night Zwift racing league not in system
- AI doesn't know this is a fixed weekly commitment
- Generates plans that might conflict

**Solution:**

- [ ] Add `recurring_commitments` to coaching_notes.json:
  ```json
  "recurring_commitments": {
    "tuesday_night": {
      "activity": "Zwift Racing League",
      "duration": "60-75 min",
      "intensity": "High (race effort)",
      "tss_estimate": "80-120",
      "notes": "Fixed weekly commitment, plan around this"
    }
  }
  ```
- [ ] Update prompt to inform AI of these constraints
- [ ] AI should avoid scheduling hard workouts the day after

### 3. Upcoming Event/Constraint Management ❌

**Problem:**

- December heat chamber research sessions not tracked
- No way to communicate upcoming schedule changes
- AI can't plan around future constraints

**Solution:**

- [ ] Add `upcoming_constraints` to coaching_notes.json:
  ```json
  "upcoming_constraints": [
    {
      "start_date": "2025-12-XX",
      "end_date": "2025-12-XX",
      "constraint_type": "research_session",
      "description": "Heat chamber testing - reduced training capacity",
      "impact": "Limit to easy/recovery workouts during this period"
    }
  ]
  ```
- [ ] Prompt AI to consider constraints in next 2-4 weeks
- [ ] AI adjusts volume/intensity accordingly

### 4. AI Should Update Coaching Notes ❌

**Problem:**

- No continuity between weeks
- Coaching observations not being saved by AI
- Each week starts fresh without context from previous AI interactions

**Solution:**

- [ ] After successful coaching session:
  - AI provides `coaching_note_update` in response
  - Save key observations to coaching_notes.json
  - Include in next week's prompt for continuity
- [ ] Structure:
  ```json
  {
    "week_number": 52,
    "ai_observations": "Athlete responding well to Sweet Spot work...",
    "areas_to_monitor": ["recovery after Tuesday races", "TSS progression"],
    "next_week_priorities": ["maintain Z2 volume", "introduce VO2max work"]
  }
  ```

## Implementation Priority

### Phase 3.5 - Context Enhancements (High Priority)

**Goal:** Fix immediate data quality issues before building UI

1. **Cross-Training Classifier** (1-2 hours)

   - Extend workout_type_analyzer.py
   - Add HR-based run classification
   - Recognize strength/mobility from titles

2. **Enhanced Coaching Notes** (30 min)

   - Add recurring_commitments field
   - Add upcoming_constraints field
   - Update coaching_notes.json with your schedule

3. **AI Context Improvements** (1 hour)

   - Update prompts to include cross-training details
   - Add recurring commitments to analysis context
   - Include upcoming constraints in generation

4. **AI Feedback Loop** (1 hour)
   - Modify generate_workout_plan to return coaching updates
   - Save AI observations to coaching_notes.json
   - Load previous week's AI notes in next session

### Phase 4 - Streamlit UI (After fixes)

**Goal:** User-friendly interface for weekly coaching

- Input form for constraints
- Display analysis + plan
- Approve/edit workflow
- Trigger Zwift file generation

## Expected Improvements

### Before (Current):

```
AI: "28.6% unclassified workouts - improve categorization"
```

### After (Fixed):

```
AI: "Great cross-training week:
- 21 bike workouts (Recovery: 6, Threshold: 2, Endurance: 2, Race: 3)
- 5 runs (4 easy Z2, 1 tempo - excellent aerobic support)
- 2 mobility sessions (yoga, stretching - good for recovery)

Note: Tuesday Zwift races providing regular high-intensity stimulus.
Recommend: Add 1 threshold bike session mid-week to complement racing."
```

## Notes

- Cross-training is CRITICAL for Jake's goals (well-rounded fitness, injury prevention, seasonal variety)
- Tuesday races = weekly high-intensity stimulus (must be accounted for in periodization)
- Heat chamber sessions = major upcoming constraint (need conservative planning)
- AI continuity = better coaching over time (learns what works, adapts approach)

## Next Steps

1. Implement cross-training classifier
2. Update coaching_notes.json with schedule
3. Test with real data
4. Then move to UI (Phase 4)

**Estimated Time:** 3-4 hours to fix all context issues
**Impact:** Massively improved AI coaching quality and relevance
