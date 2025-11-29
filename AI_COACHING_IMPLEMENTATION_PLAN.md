# AI Coaching System - Implementation Plan

## Overview

Build a fully automated AI coaching system that analyzes workout data and generates proposed workouts, while maintaining all existing manual workflows.

## Phase 1: Foundation & Infrastructure (Week 1)

**Goal**: Set up core infrastructure without disrupting existing app

### Tasks:

1. **API Configuration**

   - Add Anthropic API key to `.env.example`
   - Create `ai_coach_config.py` with model settings (allow switching between Claude Sonnet/Haiku/free models)
   - Implement cost tracking mechanism

2. **Coaching Notes System**

   - Design coaching notes JSON schema:
     ```json
     {
       "athlete_profile": {
         "goals": ["Improve FTP", "50-100mi gravel rides in Oregon"],
         "preferences": {
           "weekly_hours": "7-14 hours",
           "weekend_availability": "more flexible",
           "seasonal_focus": "winter: XC skiing, spring/fall: running/hiking, year-round: cycling"
         }
       },
       "coaching_observations": [
         {
           "date": "2025-11-12",
           "note": "Athlete showing strong consistency in training",
           "focus_areas": ["power consistency", "endurance building"]
         }
       ],
       "personality": {
         "style": "data-driven, encouraging, scientific",
         "coach_voice": "professional yet personable"
       },
       "next_week_focus": "Build aerobic base with longer Z2 rides"
     }
     ```
   - Create `data/coaching_notes.json` (gitignored for privacy)
   - Build read/write functions in `src/utils/coaching_notes.py`

3. **Database Query Tool**
   - Create `src/utils/ai_database_queries.py`
   - Implement safe, read-only SQL query functions:
     - Get last N weeks of workouts
     - Calculate weekly TSS trends
     - Get workout type distribution
     - Analyze compliance (planned vs completed)
     - FTP progression over time
     - Heart rate and power trends

**Deliverables**:

- Configuration files ready
- Coaching notes system functional
- Database query utilities tested
- No changes to existing UI yet

---

## Phase 2: Knowledge Base & Prompt Engineering (Week 1-2)

**Goal**: Create the AI coach's "brain" with cycling science knowledge

### Tasks:

1. **Export Claude Project Resources**

   - Export your existing Claude Project knowledge files
   - Organize into categories:
     - Cycling science principles
     - Training periodization concepts
     - Workout JSON schema requirements
     - Example workout files
     - Recovery and adaptation principles

2. **Create System Prompts**

   - Design master system prompt in `src/utils/ai_prompts.py`:

     ```python
     COACH_SYSTEM_PROMPT = """
     You are an elite endurance cycling coach specializing in gravel racing...

     ATHLETE PROFILE:
     - Goal: 50-100 mile gravel rides in Oregon with significant climbing
     - Current FTP: {current_ftp}W (increased from {starting_ftp}W)
     - Training availability: 1-2 hours weekdays, flexible weekends
     - Seasonal preferences: {seasonal_info}

     COACHING PHILOSOPHY:
     - Data-driven, scientifically backed training
     - Progressive overload with proper recovery
     - Polarized training model (80/20 rule)
     - Periodization for long-term development

     YOUR TASK:
     1. Analyze the weekly training summary
     2. Review historical trends from database
     3. Reference your coaching notes for continuity
     4. Generate next week's training plan
     5. Update coaching notes with observations

     OUTPUT REQUIREMENTS:
     - Weekly analysis (markdown format)
     - 7-day workout plan (JSON matching schema)
     - Updated coaching notes
     """
     ```

3. **Workout Generation Prompt**
   - Create specialized prompt for JSON generation
   - Include schema validation rules
   - Provide example outputs

**Deliverables**:

- Knowledge base organized in `docs/ai_knowledge/`
- System prompts created and tested
- Prompt templates for different scenarios

---

## Phase 3: AI Coach Core Engine (Week 2)

**Goal**: Build the AI analysis and generation engine

### Tasks:

1. **Create AI Coach Class**

   - File: `src/utils/ai_coach.py`
   - Methods:
     ```python
     class AICoach:
         def __init__(self, model="claude-sonnet-4", api_key=None)

         def analyze_weekly_summary(self, summary_text: str,
                                   historical_context: dict,
                                   coaching_notes: dict,
                                   user_constraints: str) -> dict:
             """
             Returns:
             {
                 "analysis": "markdown formatted analysis",
                 "proposed_workouts": {...},  # JSON matching schema
                 "updated_coaching_notes": {...},
                 "cost": 0.45  # API cost tracking
             }
             """

         def query_database_context(self, weeks_back=4) -> dict

         def validate_workout_json(self, workout_json: dict) -> tuple[bool, list]

         def calculate_weekly_tss_target(self, recent_tss: list) -> int
     ```

2. **Implement Analysis Logic**

   - Weekly performance analysis
   - Trend identification
   - Recovery assessment
   - Workout type balance

3. **Implement Workout Generation**
   - Use historical patterns
   - Apply periodization principles
   - Respect user constraints
   - Balance intensity distribution

**Deliverables**:

- Fully functional `AICoach` class
- Unit tests for key methods
- Cost tracking working

---

## Phase 4: Streamlit UI Integration (Week 2-3)

**Goal**: Create user-friendly interface in Streamlit

### Tasks:

1. **Create New "AI Coach" Tab**

   - Add to main Streamlit navigation
   - Design workflow:
     ```
     [Select Week] → [Add Constraints] → [Generate Analysis]
     → [Review Results] → [Approve/Edit Workouts] → [Process & Save]
     ```

2. **Build Input Form**

   ```python
   # Weekly constraints input
   st.text_area("Weekly Notes & Scheduling Constraints",
                placeholder="E.g., 'Snow on mountain - add XC skiing workout Thursday'")

   st.multiselect("Preferred Workout Types",
                  ["Cycling", "Running", "XC Skiing", "Strength", "Yoga"])

   st.slider("Target Weekly Hours", 5, 20, 10)
   ```

3. **Build Results Display**
   - Collapsible sections:
     - 📊 Weekly Performance Analysis
     - 🎯 Coaching Insights & Observations
     - 📅 Proposed Workout Plan (7 days)
     - 💭 Coach's Notes (what to focus on next week)
4. **Build Approval Workflow**
   - Display proposed workouts in readable format
   - Allow inline editing of workouts
   - "Approve & Generate Zwift Files" button
   - "Save to Proposed Workouts" button

**Deliverables**:

- New AI Coach tab functional
- User can input constraints
- Results displayed clearly
- Approval workflow working

---

## Phase 5: Validation & Integration (Week 3)

**Goal**: Connect AI output to existing app features

### Tasks:

1. **Multi-Layer Validation**

   - JSON schema validation
   - Workout parameter bounds:
     - Power zones: 0.45-1.2 FTP
     - Duration: 30-180 minutes
     - TSS: 20-250 per workout
     - Weekly TSS: 300-700
   - Activity type validation
   - Date validation

2. **Integration with Existing Features**

   - Save approved JSON to `proposed_workouts` table
   - Trigger Zwift file generation automatically
   - Update weekly dashboard
   - Generate updated weekly summary with new workouts

3. **Error Handling**
   - API failures (retry logic)
   - Invalid JSON (show errors, allow retry)
   - Database errors (rollback, show message)
   - Cost limits (warn if approaching threshold)

**Deliverables**:

- Validation system working
- Seamless integration with existing features
- Comprehensive error handling

---

## Phase 6: Testing & Refinement (Week 3-4)

**Goal**: Test with real data and refine based on results

### Tasks:

1. **Test with Historical Weeks**

   - Run AI coach on past 4 weeks
   - Compare AI-generated plans to your actual plans
   - Evaluate quality of analysis

2. **Cost Optimization**

   - Test with different models (Haiku vs Sonnet)
   - Implement caching for repeated queries
   - Optimize prompt length

3. **Quality Improvements**

   - Refine system prompts based on output quality
   - Add more specific coaching principles
   - Improve workout variety and creativity

4. **Documentation**
   - User guide for AI Coach feature
   - Developer notes for prompt tuning
   - Cost tracking and model selection guide

**Deliverables**:

- Tested with multiple weeks
- Quality meets standards
- Documentation complete

---

## Phase 7: Polish & Optional Features (Week 4+)

**Goal**: Add nice-to-have features and polish

### Optional Enhancements:

1. **Coaching Personality Customization**

   - Select coaching style: "data-focused", "motivational", "tough love"
   - Upload custom coaching preferences

2. **Multi-Week Planning**

   - Generate 2-4 week training blocks
   - Periodization across weeks
   - Event-based planning (race prep)

3. **Feedback Loop**

   - Mark completed workouts as "too hard" / "too easy"
   - AI adjusts future difficulty based on feedback

4. **Cost Dashboard**
   - Track monthly AI costs
   - Compare model costs
   - Budget alerts

---

## Success Criteria

- [ ] AI coach generates valid workout JSON 95%+ of time
- [ ] Weekly analysis feels personalized and insightful
- [ ] Coaching notes maintain continuity week-to-week
- [ ] User constraints properly incorporated
- [ ] All existing manual features still work
- [ ] Cost per week < $1.00 (target $0.25-0.50)
- [ ] Validation catches all invalid outputs
- [ ] Integration with Zwift generation seamless

---

## Risk Mitigation

1. **API Failures**: Implement retry logic, allow manual retry, cache previous successful outputs
2. **Invalid JSON**: Multiple validation layers, show specific errors, allow manual editing
3. **Cost Overruns**: Set hard limits, warn before expensive operations, test with cheaper models first
4. **Quality Issues**: Start with conservative prompts, iterate based on real outputs, maintain manual override

---

## Development Approach

- Build incrementally, test each phase thoroughly
- Keep all existing features working (never break manual workflow)
- Start with cheaper models, upgrade as needed for quality
- Collect feedback after each phase
- Be prepared to iterate on prompts significantly
