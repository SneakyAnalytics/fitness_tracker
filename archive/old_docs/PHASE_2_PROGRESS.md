# Phase 2: Knowledge Base & Prompt Engineering - IN PROGRESS 🚧

**Status**: Task 1 Complete, Task 2-4 In Progress
**Started**: November 13, 2025

## ✅ Task 1: Workout Type Analysis System

**Files**:

- `src/utils/workout_type_analyzer.py` (450 lines)
- Enhanced `src/utils/ai_database_queries.py` with workout type integration

### Features Implemented:

- **Automatic Workout Classification**:

  - Recovery workouts (28.6% of recent training)
  - Endurance workouts (9.5%)
  - Tempo workouts (4.8%)
  - Threshold workouts (9.5%)
  - VO2max workouts (4.8%)
  - Race/Event (14.3%)
  - Test protocols (FTP tests, ramp tests)

- **Pattern Recognition**:

  - Title-based classification (regex patterns)
  - Intensity Factor validation
  - Handles Zwift naming conventions

- **Progression Analysis**:

  - Week-by-week breakdown
  - Power/IF trends (improving, stable, declining)
  - Average metrics calculation
  - Historical comparison

- **Periodization Insights**:
  - Workout type distribution
  - Endurance:Threshold ratio (10:9 - moderate threshold emphasis)
  - Training phase identification

### Test Results:

```
Last 4 Weeks Distribution:
  Recovery       :  6 (28.6%)
  Unclassified   :  6 (28.6%)  ← Need better classification
  Race/Event     :  3 (14.3%)
  Threshold      :  2 ( 9.5%)
  Endurance      :  2 ( 9.5%)
  VO2max         :  1 ( 4.8%)
  Tempo          :  1 ( 4.8%)

Last 12 Weeks Progressions:
  Threshold: 9 workouts, avg power 221W [stable]
  VO2max: 5 workouts, avg power 215W [stable]
  Endurance: 10 workouts, avg power 199W [improving] ⬆️
  Tempo: 6 workouts, avg power 203W [stable]
```

### Integration:

- `get_comprehensive_context()` now includes:
  - `workout_type_distribution`: Current phase breakdown
  - `workout_type_progressions`: Trends for 4 key workout types
  - Enables AI to understand periodization patterns

---

## 🚧 Task 2: RAG Context Integration (Next)

### Available Knowledge Base Files:

Located in `data/rag_context/`:

1. **json_output_requirements.md** - Workout JSON schema
2. **updated_best_practices_document.md** - 664 lines of cycling science
3. **Latest Research Findings.md** - Current exercise science
4. **endurance notes.md** - Endurance training principles
5. **off-road cycling.md** - Gravel/MTB specifics
6. **practical applications.md** - Real-world coaching
7. Additional documents

### Planned Implementation:

- Load all markdown files
- Parse into structured knowledge chunks
- Index by topic (periodization, zones, FTP, intervals, etc.)
- Token budget management (<100K tokens for context)

---

## 🚧 Task 3: System Prompt Creation (Next)

### Components to Build:

1. **Master Coaching Personality**

   - Data-driven, encouraging, scientific approach
   - Reference coaching notes personality
   - Voice consistency

2. **Core Training Principles**

   - Periodization (base → build → peak → recovery)
   - Progressive overload
   - Specificity principle
   - Recovery importance

3. **Safety Guardrails**

   - Max TSS per week limits
   - Recovery requirements
   - Injury prevention
   - Overtraining detection

4. **Output Format Requirements**
   - JSON schema adherence
   - FTP-based zone calculation
   - Duration units (minutes)
   - Interval structure validation

---

## 🚧 Task 4: Specialized Prompts (Next)

### Prompt Types Needed:

1. **Weekly Analysis Prompt**

   - Input: Weekly summary + comprehensive context
   - Output: Observations, insights, recommendations

2. **Workout Generation Prompt**

   - Input: Analysis + athlete constraints + goals
   - Output: 7-day workout plan JSON

3. **JSON Validation Prompt**
   - Input: Generated JSON
   - Output: Validation report + corrections

---

## Current Capabilities

### Data Available to AI Coach:

✅ 4-week training history (weekly TSS, hours, compliance)
✅ FTP progression tracking
✅ Power/HR trends
✅ Workout type distribution & progressions
✅ Recent 15 workouts with full metrics
✅ Athlete profile (FTP 300W, goals, preferences)
✅ Coaching notes (observations, personality, training phase)

### Missing for Full Implementation:

⏳ RAG context loader
⏳ System prompts
⏳ Specialized prompts
⏳ Token budget optimizer
⏳ Prompt template engine

---

## Next Immediate Steps:

1. Create `src/utils/rag_context_loader.py`

   - Load markdown files
   - Parse into chunks
   - Index by topic

2. Create `src/utils/ai_prompts.py`

   - System prompt templates
   - Weekly analysis prompt
   - Workout generation prompt

3. Test prompt with Gemini Free
   - Validate JSON output
   - Check coaching quality
   - Measure token usage

---

## Notes & Observations:

### Workout Classification Accuracy:

- 71.4% successfully classified (15/21 workouts)
- 28.6% "Unclassified" - mostly outdoor rides and group events
- Consider adding:
  - "Group Ride" category
  - "Outdoor/Unstructured" category
  - Better handling of race simulations

### Interesting Findings:

- Heavy recovery emphasis (28.6%) - good recovery practice
- Endurance power trending up (improving) - base fitness building
- Balanced periodization (10:9 endurance:threshold ratio)
- Limited VO2max work in last 4 weeks (4.8%) - might be periodization phase

### AI Coach Potential Insights:

With workout type analysis, AI can now:

- Detect when athlete is in base/build/peak phase
- Recommend periodization adjustments
- Notice missing workout types
- Track progression within specific zones
- Compare current week to historical patterns

---

**Time Estimate for Phase 2 Completion**: 2-3 hours
**Blocking Issues**: None
**Ready to Continue**: Yes ✅
