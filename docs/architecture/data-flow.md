# Daily Automation - Data Flow & Duplicate Prevention

## ✅ What Gets Downloaded & Uploaded

### Complete Data Flow:

```
TrainingPeaks Export (3 files)
    ├── WorkoutFileExport-*.zip     → FIT files → Uploaded to /upload/fit
    ├── WorkoutExport-*.zip         → workouts.csv → Uploaded to /upload/workouts
    └── MetricsExport-*.zip         → metrics.csv → Uploaded to /upload/metrics

Then:
    → FIT files parsed & analyzed by Gemini AI
    → Results stored in workout_analyses table
    → Personal bests tracked
    → All temp files cleaned up
```

### You get ALL three file types automatically:

1. **FIT Files** - Raw workout data (power, HR, cadence, GPS)
   - Parsed and analyzed by Gemini AI
   - Stored in database with coaching insights
2. **Workouts CSV** - Workout summary data
   - Name, date, duration, TSS, IF, NP, etc.
   - Uploaded to database via `/upload/workouts` endpoint
3. **Metrics CSV** - Custom metrics and performance data
   - Training metrics, wellness scores, etc.
   - Uploaded to database via `/upload/metrics` endpoint

**Result:** You never need to run the manual data upload tool! 🎉

---

## 🔄 Duplicate Prevention (Upsert Behavior)

### The Problem:

When testing, running the analysis multiple times on the same workout would create duplicate entries:

- 25 analysis records for 1 workout ❌
- Confusing weekly summaries ❌
- Potential downstream issues ❌

### The Solution:

Implemented **UPSERT** behavior in `store_workout_analysis()`:

```python
# Check if analysis already exists for this workout
if workout_id:
    existing = db.query("SELECT id FROM workout_analyses WHERE workout_id = ?")
    if existing:
        # UPDATE existing record
        db.execute("UPDATE workout_analyses SET ... WHERE id = ?")
    else:
        # INSERT new record
        db.execute("INSERT INTO workout_analyses ...")
```

### Benefits:

- ✅ **Testing friendly**: Run analysis 10 times, only 1 record exists
- ✅ **Latest data wins**: Always overwrites with newest analysis
- ✅ **Clean database**: No duplicate confusion
- ✅ **Timestamp updated**: `analyzed_at` reflects last analysis time

### Example:

```bash
# First run
python -m src.utils.daily_auto_sync_and_analyze
→ Creates analysis ID 123 for workout_id 456

# Second run (testing)
python -m src.utils.daily_auto_sync_and_analyze
→ Updates analysis ID 123 (no new record)

# Third run (testing)
python -m src.utils.daily_auto_sync_and_analyze
→ Updates analysis ID 123 again (still no new record)

# Database: Still only 1 record! ✅
```

---

## 🗄️ Database Schema Updates

### New Columns Added:

```sql
ALTER TABLE workout_analyses ADD COLUMN analysis_data TEXT;
ALTER TABLE workout_analyses ADD COLUMN peak_efforts TEXT;
```

**Automatic migration**: The database automatically adds these columns if they don't exist.

### Data Structure:

**`analysis_data`** (JSON):

```json
{
  "quality_rating": 8,
  "effort_distribution": "70% Zone 4-5, 20% Zone 2-3",
  "notable_achievements": "New 20min power PR",
  "recovery_recommendations": "Recommend 48hrs before next hard session",
  "performance_insights": "Power very consistent, slight HR drift"
}
```

**`peak_efforts`** (JSON):

```json
{
  "30s": 450.2,
  "1min": 420.5,
  "3min": 380.1,
  "5min": 365.3,
  "10min": 340.2,
  "20min": 320.5,
  "60min": 280.0
}
```

---

## 🧪 Testing Multiple Times

### Scenario: Testing the same workout 5 times

```bash
# Run 1
streamlit → Run Automation → Select Nov 17
→ Analysis created: ID 100

# Run 2 (fixing something)
streamlit → Run Automation → Select Nov 17
→ Analysis updated: ID 100 (no duplicate!)

# Run 3 (testing again)
streamlit → Run Automation → Select Nov 17
→ Analysis updated: ID 100 (still no duplicate!)

# Run 4 (final test)
streamlit → Run Automation → Select Nov 17
→ Analysis updated: ID 100 (clean!)

# Run 5 (just to be sure)
streamlit → Run Automation → Select Nov 17
→ Analysis updated: ID 100 (perfect!)
```

**Database**: Only 1 record exists for the workout ✅

---

## 📊 Weekly Summary Behavior

### When you generate next week's plan:

```python
# Gets AI analyses for the week
analyses = db.get_weekly_workout_analyses('2025-11-11', '2025-11-17')

# Result: 1 analysis per workout (latest version)
[
    {
        'workout_id': 123,
        'workout_date': '2025-11-11',
        'analysis_data': {...},  # Latest analysis
        'analyzed_at': '2025-11-18T14:30:00'  # Last updated
    },
    {
        'workout_id': 124,
        'workout_date': '2025-11-13',
        'analysis_data': {...},
        'analyzed_at': '2025-11-18T14:35:00'
    }
]
```

**No duplicates, just clean data!** 🎉

---

## 🔧 Manual Testing Commands

### Test the complete automation:

```bash
cd /Users/jacobrobinson/fitness_tracker
source venv/bin/activate
python -m src.utils.daily_auto_sync_and_analyze
```

### Check for duplicates in database:

```bash
sqlite3 data/fitness_data.db

-- Count analyses per workout (should all be 1)
SELECT workout_id, COUNT(*) as count
FROM workout_analyses
WHERE workout_id IS NOT NULL
GROUP BY workout_id
HAVING count > 1;

-- Should return no rows if working correctly!
```

### View latest analyses:

```bash
sqlite3 data/fitness_data.db

SELECT
    w.workout_date,
    w.workout_name,
    wa.analyzed_at,
    COUNT(*) as analysis_count
FROM workouts w
LEFT JOIN workout_analyses wa ON w.id = wa.workout_id
GROUP BY w.id
ORDER BY w.workout_date DESC
LIMIT 10;
```

---

## 🎯 Complete Workflow Summary

### Daily Automation (10pm PST):

1. **Login** → TrainingPeaks via Playwright
2. **Download** → 3 files (FIT, workouts CSV, metrics CSV)
3. **Upload** → All 3 files to database
4. **Parse** → FIT file data (power, HR, zones)
5. **Analyze** → Gemini AI coaching insights
6. **Store** → Analysis in database (UPSERT)
7. **Track** → Personal bests
8. **Cleanup** → Delete temp files

### Weekly Planning (manual):

1. **Retrieve** → All daily analyses for the week
2. **Aggregate** → Weekly summary with AI insights
3. **Analyze** → Claude reviews week
4. **Generate** → Next week's workout plan
5. **Export** → Zwift .zwo files

### Result:

- ✅ All data automatically synced
- ✅ No manual uploads needed
- ✅ No duplicate analyses
- ✅ AI-driven periodization
- ✅ Clean, efficient workflow

---

## 🚀 Ready to Use

### Setup (one time):

```bash
pip install playwright
playwright install chromium
```

### Daily Use:

**Option 1** - Streamlit UI:

- Go to Performance Analytics tab
- Select date
- Click "Run Complete Automation Now"

**Option 2** - Cron (automated):

```bash
0 22 * * * cd /Users/jacobrobinson/fitness_tracker && venv/bin/python -m src.utils.daily_auto_sync_and_analyze
```

### Testing (as many times as you want):

- Run automation multiple times
- Check database: `SELECT COUNT(*) FROM workout_analyses;`
- Count should match number of unique workouts, not number of test runs!
