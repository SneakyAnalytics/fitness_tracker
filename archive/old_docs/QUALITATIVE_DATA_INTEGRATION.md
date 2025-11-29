# Qualitative Data Integration for AI Coach

## Issue Identified

The AI Coach workflow was **not** receiving user-submitted qualitative data (muscle soreness patterns and fatigue levels) that you manually enter in the Weekly Summary interface. This data is valuable for:

1. **Injury Prevention** - Identifying areas that need targeted mobility work or rest
2. **Fatigue Management** - Understanding when Garmin's energy metrics don't match subjective feelings
3. **Workout Customization** - Tailoring strength work to address specific weaknesses
4. **Recovery Planning** - Adjusting training load when you're more tired than metrics suggest

## What Was Missing

### Weekly Summary Interface Collects:

- **Muscle Soreness Assessment:**

  - Checkbox selection: Quads, Hamstrings, Calves, Lower Back, Upper Back, Core, Other
  - Severity slider: 1-5 scale
  - Free text details about patterns, triggers, recovery observations

- **Fatigue Assessment:**
  - Energy pattern dropdown: "Strong in morning, declining later", "Consistently low energy", etc.
  - Impact checkboxes: Sleep Quality, Workout Performance, Daily Activities, Mental Focus, Recovery Time
  - Free text details about energy level patterns

### Database Storage:

- Stored in `weekly_summaries` table, `qualitative_data` JSON field
- Fields: `muscle_soreness_patterns` and `general_fatigue_level`
- Function exists: `get_weekly_summary_qualitative_data(start_date, end_date)`

### The Problem:

- `generate_weekly_summary()` function **did not call** `get_weekly_summary_qualitative_data()`
- AI Coach received workout metrics but **not** your subjective feedback
- Coach couldn't see: "Lower back sore after long ride" or "Needed nap after weekend ride despite Garmin showing 40% energy"

## Solution Implemented

### Code Change:

Updated `src/storage/database.py` line ~1378-1390 in `generate_weekly_summary()`:

```python
# Add weekly plan and any unmatched proposed workouts to summary
summary.update({
    'weekly_plan': weekly_plan_data,
    'proposed_workouts': proposed_workouts
})

# Add qualitative data (muscle soreness and fatigue patterns) if available
qual_data = self.get_weekly_summary_qualitative_data(start_date, end_date)
if qual_data:
    print(f"\nDEBUG: Adding qualitative data to summary: {json.dumps(qual_data, indent=2)}")
    summary['muscle_soreness_patterns'] = qual_data.get('muscle_soreness_patterns')
    summary['general_fatigue_level'] = qual_data.get('general_fatigue_level')

return summary
```

### What This Fixes:

1. **Automatic Integration** - No workflow changes needed
2. **Backward Compatible** - Works with or without qualitative data
3. **AI Context Enhanced** - Coach now sees complete picture

## How It Works Now

### Complete AI Coach Workflow:

1. **User Creates Weekly Summary (Manual Process)**

   - Upload FIT files for the week
   - Fill out muscle soreness checkboxes and severity
   - Fill out fatigue pattern and impact areas
   - Save weekly summary → data stored in database

2. **User Opens AI Coach Tab**

   - Select the same week dates
   - (Optional) Add additional context in text boxes

3. **User Clicks "Generate AI Analysis"**

   - `generate_weekly_summary()` retrieves:
     - ✅ Workout metrics (TSS, duration, power, HR)
     - ✅ Sleep quality data
     - ✅ Energy levels
     - ✅ **NEW:** Muscle soreness patterns
     - ✅ **NEW:** General fatigue levels
   - AI receives complete picture including subjective feedback
   - AI can reference: "Lower back soreness" when planning mobility work
   - AI can consider: "Energy didn't match Garmin metrics" when planning recovery

4. **AI Generates Personalized Plan**
   - Can suggest: "Extra lower back stretches in mobility session"
   - Can adjust: "Adding recovery day given fatigue mismatch with device metrics"
   - Can target: "Strength work focusing on core to address lower back issues"

## Example Use Cases

### Case 1: Post-Long-Ride Fatigue

**Your Input (Weekly Summary):**

- Fatigue Pattern: "Consistently low energy"
- Impact: ✓ Needed Extra Recovery Time
- Details: "Took 2-hour nap after 4-hour Saturday ride, Garmin showed 40% energy but felt exhausted"

**AI Coach Now Sees:**

```json
{
  "general_fatigue_level": "Energy Pattern: Consistently low energy\nImpact Areas: Needed Extra Recovery Time\nDetails: Took 2-hour nap after 4-hour Saturday ride, Garmin showed 40% energy but felt exhausted"
}
```

**AI Can Respond:**
"Despite device metrics showing moderate energy (40%), your subjective fatigue requiring a 2-hour nap indicates deeper physiological stress. Recommend extra recovery day mid-week and reduced intensity for Tuesday's intervals."

### Case 2: Recurring Lower Back Soreness

**Your Input (Weekly Summary):**

- Soreness Areas: ✓ Lower Back
- Severity: 4/5
- Details: "Particularly sore after Wednesday's long ride, felt tight during Thursday run"

**AI Coach Now Sees:**

```json
{
  "muscle_soreness_patterns": "Severity: 4/5\nAreas: Lower Back\nDetails: Particularly sore after Wednesday's long ride, felt tight during Thursday run"
}
```

**AI Can Respond:**
"Lower back soreness (4/5 severity) suggests need for targeted work. This week's mobility session will include extra lower back stretches and hip flexor work. Strength sessions will focus on core stability to address root cause."

### Case 3: No Qualitative Data

**Your Input:** (Skip weekly summary)

**AI Coach Sees:**

- Workout metrics only
- No `muscle_soreness_patterns` or `general_fatigue_level` fields

**AI Works Normally:**

- Still generates analysis and plan
- Uses objective metrics (TSS, power, HR, sleep, energy)
- Qualitative data is optional enhancement, not required

## Testing

### Test Scenario 1: With Qualitative Data

1. Create weekly summary for Nov 4-10, 2025 with soreness/fatigue data
2. Go to AI Coach, select same dates
3. Click "Generate AI Analysis"
4. Verify analysis mentions your soreness or fatigue patterns
5. Generate workout plan
6. Verify plan addresses specific issues you reported

### Test Scenario 2: Without Qualitative Data

1. Select a week with NO weekly summary (only raw workouts)
2. Go to AI Coach, select those dates
3. Click "Generate AI Analysis"
4. Should work normally with just objective metrics
5. No errors about missing data

### Verify Database Query:

```python
from src.storage.database import WorkoutDatabase
db = WorkoutDatabase()

# Check what data exists for a week
qual_data = db.get_weekly_summary_qualitative_data('2025-11-04', '2025-11-10')
print(qual_data)

# Check what AI Coach receives
summary = db.generate_weekly_summary('2025-11-04', '2025-11-10')
print(summary.get('muscle_soreness_patterns'))
print(summary.get('general_fatigue_level'))
```

## Benefits

1. **More Accurate Recovery Planning** - AI knows when you're truly fatigued vs. device metrics
2. **Targeted Injury Prevention** - Can suggest specific mobility/strength work for sore areas
3. **Personalized Progressions** - Understands when to push vs. when to back off
4. **Holistic View** - Combines objective data (power, HR) with subjective experience
5. **No Extra Work** - Uses data you're already entering in Weekly Summary
6. **Optional Enhancement** - Works with or without this data

## Next Steps (Optional Enhancements)

1. **Prompt Engineering** - Update RAG context to specifically highlight how to use soreness/fatigue data
2. **Trending Analysis** - Track soreness patterns across weeks ("Lower back issues recurring")
3. **Predictive Alerts** - "You've reported quad soreness 3 weeks in a row, consider bike fit check"
4. **UI Indicators** - Show badge on AI Coach when qualitative data is available for selected week
5. **Continuity Integration** - Save soreness trends in coaching_notes.json for long-term memory

## Technical Details

### Database Schema:

```sql
CREATE TABLE weekly_summaries (
    id INTEGER PRIMARY KEY,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    summary_data TEXT,  -- JSON with metrics
    qualitative_data TEXT,  -- JSON with soreness/fatigue
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Qualitative Data JSON Structure:

```json
{
  "muscle_soreness_patterns": "Severity: 4/5\nAreas: Lower Back, Quads\nDetails: Tight after long rides",
  "general_fatigue_level": "Energy Pattern: Strong in morning, declining later\nImpact Areas: Workout Performance\nDetails: Struggled with afternoon intervals"
}
```

### Functions Involved:

- `save_weekly_summary()` - Saves qualitative data to database
- `get_weekly_summary_qualitative_data()` - Retrieves qualitative data
- `generate_weekly_summary()` - **NOW** includes qualitative data in output
- `analyze_week()` - Receives enhanced summary with qualitative data
