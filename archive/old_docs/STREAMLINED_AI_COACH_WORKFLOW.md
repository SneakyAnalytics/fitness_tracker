# Streamlined AI Coach Workflow

## User's Preferred Workflow

Your ideal weekly workflow (as clarified):

1. **During the Week**: View schedule day-over-day in the app
2. **End of Week**: Go to "Import Data" page → automatically retrieve and parse data from TrainingPeaks
3. **AI Coaching**: Swap to "AI Coach" tab → Fill out everything in ONE place:
   - Schedule constraints for upcoming week
   - Training focus and goals
   - Feedback from completed week
   - **Muscle soreness assessment** (checkboxes, severity, details)
   - **Fatigue assessment** (energy pattern, impact areas, details)
4. **Generate**: Click one button to analyze the week and generate next week's plan
5. **Done**: All in one place, no jumping between multiple tabs

## What Changed

### ❌ OLD (Convoluted) Workflow:

1. Import Data page → upload FIT files
2. Weekly Summary page → fill out soreness/fatigue
3. AI Coach page → fill out context and generate plan
4. **Problem**: Too many steps, repetitive navigation

### ✅ NEW (Streamlined) Workflow:

1. Import Data page → upload FIT files (TrainingPeaks integration)
2. **AI Coach page → Everything in one place:**
   - User context (schedule, focus, feedback)
   - **Muscle soreness checkboxes & details** ← NEW
   - **Fatigue assessment & details** ← NEW
   - Generate analysis
   - Generate workout plan
   - Save to database + Zwift files
3. **Done**: Single-page experience

## Implementation Details

### Code Changes (src/ui/streamlit_app.py)

**Added to AI Coach page (after Step 2 context fields):**

```python
# Soreness and Fatigue Assessment
st.markdown("---")
st.markdown("### 🏥 Soreness & Fatigue Assessment (Optional)")
st.markdown("*Help the AI understand your recovery state - especially useful when device metrics don't match how you feel*")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 🦵 Muscle Soreness")

    # Checkboxes for sore areas
    soreness_areas = {
        "Quads": st.checkbox("Quads", key="ai_soreness_quads"),
        "Hamstrings": st.checkbox("Hamstrings", key="ai_soreness_hamstrings"),
        "Calves": st.checkbox("Calves", key="ai_soreness_calves"),
        "Lower Back": st.checkbox("Lower Back", key="ai_soreness_lower_back"),
        "Upper Back": st.checkbox("Upper Back", key="ai_soreness_upper_back"),
        "Core": st.checkbox("Core", key="ai_soreness_core"),
        "Other": st.checkbox("Other", key="ai_soreness_other")
    }

    # Severity slider (1-5)
    soreness_severity = st.slider(
        "Overall Soreness Level",
        min_value=1, max_value=5, value=1,
        key="ai_soreness_severity"
    )

    # Free text details
    muscle_soreness_details = st.text_area(
        "Additional Soreness Details",
        placeholder="e.g., Lower back particularly tight after Wednesday's long ride...",
        key="ai_soreness_details"
    )

with col2:
    st.markdown("#### 😴 Fatigue Assessment")

    # Energy pattern dropdown
    energy_pattern = st.selectbox(
        "Select your typical energy pattern this week",
        options=[
            "Consistent energy throughout the day",
            "Strong in morning, declining later",
            "Low in morning, improving later",
            "Fluctuating throughout the day",
            "Consistently low energy",
            "Consistently high energy"
        ],
        key="ai_energy_pattern"
    )

    # Impact checkboxes
    fatigue_impacts = {
        "Sleep Quality": st.checkbox("Affected Sleep Quality", key="ai_fatigue_sleep"),
        "Workout Performance": st.checkbox("Affected Workout Performance", key="ai_fatigue_workout"),
        "Daily Activities": st.checkbox("Affected Daily Activities", key="ai_fatigue_daily"),
        "Mental Focus": st.checkbox("Affected Mental Focus", key="ai_fatigue_mental"),
        "Recovery Time": st.checkbox("Needed Extra Recovery Time", key="ai_fatigue_recovery")
    }

    # Free text details
    fatigue_details = st.text_area(
        "Additional Fatigue Details",
        placeholder="e.g., Needed 2-hour nap after Saturday's 4-hour ride, Garmin showed 40% energy but felt exhausted...",
        key="ai_fatigue_details"
    )
```

**Updated "Generate AI Analysis" button to include soreness/fatigue:**

```python
# Add soreness assessment to user context
sore_areas = [area for area, checked in soreness_areas.items() if checked]
if sore_areas or soreness_severity > 1 or muscle_soreness_details:
    muscle_soreness = f"Severity: {soreness_severity}/5\n"
    if sore_areas:
        muscle_soreness += f"Areas: {', '.join(sore_areas)}\n"
    if muscle_soreness_details:
        muscle_soreness += f"Details: {muscle_soreness_details}"
    user_context['muscle_soreness_patterns'] = muscle_soreness

# Add fatigue assessment to user context
impact_areas = [area for area, checked in fatigue_impacts.items() if checked]
if energy_pattern != "Consistent energy throughout the day" or impact_areas or fatigue_details:
    general_fatigue = f"Energy Pattern: {energy_pattern}\n"
    if impact_areas:
        general_fatigue += f"Impact Areas: {', '.join(impact_areas)}\n"
    if fatigue_details:
        general_fatigue += f"Details: {fatigue_details}"
    user_context['general_fatigue_level'] = general_fatigue
```

## New AI Coach Page Structure

### Step 1: Select Completed Training Week

- Date pickers for the week you just finished

### Step 2: Provide Context (Optional but Recommended)

- **Column 1:**
  - 📅 Upcoming Week Schedule & Constraints
  - 🎯 Training Focus & Goals
- **Column 2:**
  - 🗣️ Completed Week - Feedback & Feelings

### Step 3: Soreness & Fatigue Assessment (Optional) ← NEW SECTION

- **Column 1 - Muscle Soreness:**
  - Checkboxes: Quads, Hamstrings, Calves, Lower Back, Upper Back, Core, Other
  - Slider: Overall soreness level (1-5)
  - Text area: Additional details
- **Column 2 - Fatigue Assessment:**
  - Dropdown: Energy pattern throughout the day
  - Checkboxes: Impact on sleep, workouts, daily activities, mental focus, recovery
  - Text area: Additional details (especially device vs. subjective mismatch)

### Step 4: Generate Weekly Analysis

- Click button → AI analyzes completed week with all context
- AI receives:
  - Workout metrics (TSS, power, HR, sleep, energy)
  - Your schedule constraints
  - Your training focus
  - Your week feedback
  - **Your soreness assessment** ← NEW
  - **Your fatigue assessment** ← NEW

### Step 5: Generate Next Week's Workout Plan

- Click button → AI creates personalized 7-day plan
- Plan accounts for soreness (e.g., extra lower back stretches)
- Plan adjusts for fatigue mismatch (e.g., extra recovery day)

### Step 6: Save & Export

- Click button → Save to database + generate Zwift files
- View in Proposed Workouts tab
- Use .zwo files in Zwift

## Benefits of Streamlined Workflow

1. **Single Page Experience** - Everything in AI Coach tab
2. **No Jumping Around** - Don't need to visit Weekly Summary tab
3. **Contextual Flow** - Fill out everything while you're thinking about the week
4. **Faster** - Less navigation, fewer clicks
5. **Clearer** - All inputs visible together, see what AI is considering
6. **Still Optional** - Can skip soreness/fatigue if you want
7. **Same Data** - AI receives identical information as before

## Example User Session

**Monday Morning (End of Week Workflow):**

1. Open app → Go to "Import Data" tab
2. Click "Import from TrainingPeaks" (automated)
3. Go to "🤖 AI Coach" tab
4. Select dates: Oct 28 - Nov 3, 2025 (last week)
5. Fill out context:
   - **Upcoming Schedule**: "Tuesday 6pm Zwift race, Thursday travel to Denver, Saturday 3-hour outdoor ride available"
   - **Training Focus**: "Building race-specific power for Zwift TTT events"
   - **Week Feedback**: "Tuesday's threshold intervals felt strong, ready to push harder"
6. Fill out soreness:
   - ✓ Lower Back
   - ✓ Quads
   - Severity: 3/5
   - Details: "Lower back tight after Saturday's 4-hour ride, improved with stretching"
7. Fill out fatigue:
   - Energy Pattern: "Strong in morning, declining later"
   - ✓ Needed Extra Recovery Time
   - Details: "Took 2-hour nap after Saturday ride, Garmin showed 40% energy but felt completely exhausted"
8. Click "Generate AI Analysis"
9. Review analysis (mentions lower back soreness, energy mismatch)
10. Click "Generate Workout Plan"
11. Review 7-day plan (includes extra lower back mobility, adjusted recovery)
12. Click "Save Plan to Proposed Workouts & Generate Zwift Files"
13. **Done!** - Ready to train

**Total time**: 5-10 minutes, all in one tab

## Data Flow

```
TrainingPeaks Import (automated)
    ↓
FIT Files → Database
    ↓
AI Coach Tab (all in one place):
    - Select completed week
    - Fill out context (schedule, focus, feedback)
    - Fill out soreness (checkboxes, severity, details)
    - Fill out fatigue (pattern, impacts, details)
    - Click "Generate Analysis"
        ↓
    AI receives:
        - Workout data (TSS, power, HR, sleep)
        - User context (schedule, focus, feedback)
        - Soreness assessment ← From AI Coach form
        - Fatigue assessment ← From AI Coach form
        ↓
    AI generates personalized analysis
        ↓
    Click "Generate Workout Plan"
        ↓
    AI creates 7-day plan accounting for:
        - Performance trends
        - Recovery needs
        - Specific soreness areas
        - Energy mismatch with devices
        - Schedule constraints
        ↓
    Click "Save"
        ↓
    Database + Zwift .zwo files
        ↓
    Train!
```

## Comparison: Weekly Summary vs. AI Coach

### Weekly Summary Tab (Still Available):

- **Purpose**: Historical record keeping
- **Use Case**: Manually document a week for your records
- **Data Saved**: Permanently stored in `weekly_summaries` table
- **When to Use**: If you want to create a historical summary without generating a new plan

### AI Coach Tab (New Streamlined Version):

- **Purpose**: Generate next week's workout plan
- **Use Case**: Weekly workflow - analyze completed week, plan next week
- **Data Passed**: To AI as context (not permanently saved in weekly_summaries)
- **When to Use**: Every week as part of your normal workflow
- **Advantage**: All inputs in one place, immediate plan generation

## Technical Notes

- Soreness/fatigue data is passed via `user_context` parameter to AI
- Data format is identical to Weekly Summary (same strings)
- AI receives it whether entered in Weekly Summary OR AI Coach tab
- No database changes needed - data flows through existing paths
- Weekly Summary tab remains unchanged (for those who want to use it)
- AI Coach tab is now self-contained

## Testing Checklist

- [ ] AI Coach page loads without errors
- [ ] Soreness checkboxes work
- [ ] Fatigue dropdowns work
- [ ] Text areas accept input
- [ ] "Generate Analysis" includes soreness data
- [ ] "Generate Analysis" includes fatigue data
- [ ] AI response references soreness when provided
- [ ] AI response references fatigue when provided
- [ ] Workout plan accounts for specific soreness areas
- [ ] Workout plan adjusts for fatigue mismatch
- [ ] Can skip soreness/fatigue (optional)
- [ ] Can generate plan with only workout data (no context)
