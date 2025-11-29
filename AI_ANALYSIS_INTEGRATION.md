# AI Analysis Integration

## Overview

This document explains how Gemini AI workout analyses are integrated into weekly workout generation.

## Complete Data Flow

```
Daily (10pm PST):
  TrainingPeaks Login → Download FIT Files → Parse Data → Gemini AI Analysis → Store in Database
                                                                                      ↓
                                                                              workout_analyses table

Weekly (User Triggered):
  generate_weekly_summary() → Pull AI analyses → Add to summary → Claude AI Generation → Next Week's Plan
```

## Components

### 1. Daily Automation (`daily_auto_sync_and_analyze.py`)

**What it does:**

- Logs into TrainingPeaks via Playwright browser automation
- Downloads today's workout FIT files
- Parses FIT data: power, heart rate, cadence, speed, zones
- Sends data to Gemini AI (`gemini-2.0-flash-exp`) for coaching analysis
- Stores analysis in `workout_analyses` table
- Tracks personal bests in `personal_bests` table
- Cleans up temporary files

**Gemini Analysis Includes:**

- Quality rating (1-10 scale)
- Effort distribution breakdown
- Notable achievements
- Recovery recommendations
- Performance insights
- Peak efforts (7 durations: 30s, 1min, 3min, 5min, 10min, 20min, 60min)

### 2. Database Storage (`database.py`)

**Tables:**

- `workout_analyses` - Stores Gemini AI coaching insights

  - `workout_id` - Links to workouts table
  - `analysis_text` - Full text analysis from Gemini
  - `analysis_data` - JSON structured data (quality, insights, recovery)
  - `peak_efforts` - JSON peak power efforts data
  - `analyzed_at` - Timestamp
  - `model_used` - AI model identifier

- `personal_bests` - Tracks top 3 efforts
  - Effort type, value, rank (1-3), date, medal (🥇🥈🥉)

**New Method: `get_weekly_workout_analyses(start_date, end_date)`**

- Queries workout_analyses table for date range
- Joins with workouts table to get workout context
- Returns: workout name, date, type, TSS, duration, AI analysis data
- Used by weekly summary generation

### 3. Weekly Summary Generation (`database.py`)

**Integration Point (Line 1427):**

```python
# Add AI workout analyses if available
ai_analyses = self.get_weekly_workout_analyses(start_date, end_date)
if ai_analyses:
    print(f"\nDEBUG: Adding {len(ai_analyses)} AI workout analyses to summary")
    summary['ai_workout_analyses'] = ai_analyses
```

**Summary includes:**

- Total TSS, duration, session count
- Workout types distribution
- Qualitative feedback from user
- Proposed workouts
- **NEW**: AI workout analyses from Gemini

### 4. Weekly Workout Generation (`ai_coach_engine.py`)

**Process:**

1. `analyze_week()` receives weekly summary with AI analyses
2. Builds comprehensive context including Gemini insights
3. Sends to Claude AI with full context
4. Claude generates next week's workouts informed by:
   - Historical performance data
   - User feedback
   - **Gemini's daily coaching analyses**
   - Recovery recommendations
   - Performance trends

## Benefits

### Complete Coaching Loop

- **Daily**: Gemini analyzes each workout's quality, effort, recovery needs
- **Weekly**: Claude uses those insights to plan next week
- **Result**: AI-driven periodization based on actual performance

### Example Flow

1. **Monday workout**: Hard VO2max intervals
   - Gemini: "Quality 8/10, excellent power consistency, recommend 48hr recovery"
2. **Tuesday workout**: Easy recovery spin
   - Gemini: "Quality 7/10, good active recovery, HR stayed in zone 1-2"
3. **Wednesday**: Rest day
4. **Thursday workout**: Threshold intervals
   - Gemini: "Quality 9/10, new 20min power PR, athlete responding well"
5. **Sunday**: Generate next week
   - Claude sees all 3 analyses
   - Plans progressive load based on quality ratings
   - Respects recovery recommendations
   - Builds on Thursday's breakthrough

## Technical Details

### Rate Limiting

- Gemini: 10 requests/minute (6s delay between calls)
- Claude: No strict limit, uses streaming

### Data Format

AI analyses in weekly summary:

```python
{
    'ai_workout_analyses': [
        {
            'workout_id': 123,
            'workout_date': '2025-11-18',
            'workout_name': 'VO2max Intervals',
            'workout_type': 'intervals',
            'duration': 3600,
            'tss': 85,
            'analysis_text': 'Full Gemini coaching text...',
            'analysis_data': {
                'quality_rating': 8,
                'effort_distribution': {...},
                'recovery_recommendations': '...',
                'performance_insights': '...'
            },
            'peak_efforts': {
                '30s': 450,
                '1min': 420,
                '3min': 380,
                ...
            },
            'analyzed_at': '2025-11-18T22:00:00',
            'model_used': 'gemini-2.0-flash-exp'
        },
        ...
    ]
}
```

### Error Handling

- Missing analyses: Weekly summary proceeds without AI data
- Failed Gemini calls: Logged, doesn't block automation
- Database errors: Rolled back, logged with traceback

## Setup & Testing

### Verify Integration

```python
from src.storage.database import WorkoutDatabase
db = WorkoutDatabase()

# Check recent analyses
analyses = db.get_weekly_workout_analyses('2025-11-11', '2025-11-17')
print(f"Found {len(analyses)} analyses")

# Generate weekly summary
summary = db.generate_weekly_summary('2025-11-11', '2025-11-17')
if 'ai_workout_analyses' in summary:
    print(f"✅ AI analyses integrated: {len(summary['ai_workout_analyses'])} workouts")
else:
    print("❌ No AI analyses in summary")
```

### Manual Test Run

```bash
# Run daily automation
python -m src.utils.daily_auto_sync_and_analyze

# Check database
sqlite3 data/fitness_data.db "SELECT COUNT(*) FROM workout_analyses;"

# Generate next week
# Use Streamlit UI: Weekly Planning → Generate New Plan
```

## Cost Estimates

- Gemini API: ~$0.02/week (7 workouts)
- Claude API: ~$0.16/week (analysis + generation)
- **Total: ~$0.18/week** or **$9.36/year**

## Next Steps

1. ✅ Method implemented: `get_weekly_workout_analyses()`
2. ✅ Integration point added in `generate_weekly_summary()`
3. ⏸️ Test with real data
4. ⏸️ Verify Claude's prompt includes AI analyses properly
5. ⏸️ Monitor quality of generated workouts

## Troubleshooting

### No AI analyses in weekly summary

- Check: `SELECT COUNT(*) FROM workout_analyses;`
- Verify: Daily automation ran successfully
- Check logs: `tail -f logs/daily_automation.log`

### Gemini API errors

- Check API key: `GOOGLE_API_KEY` in environment
- Verify rate limits: Max 10/minute
- Check quota: Gemini API dashboard

### Missing workout associations

- FIT files must be downloaded via automation
- Manual FIT files won't have workout_id association
- Use fit_file_id for orphaned analyses
