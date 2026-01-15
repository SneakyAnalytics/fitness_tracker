# Database Schema Documentation

## Overview

The fitness tracker uses SQLite for data storage. The database file is located at `data/fitness_data.db` and contains workout data, FIT file analysis, AI coaching plans, and athlete settings.

**Key Design Principles:**

- JSON columns for flexible, schema-less data storage
- Foreign key relationships to maintain data integrity
- Backup tables for critical data migrations
- Indexes for performance optimization

## Core Tables

### `workouts`

Stores completed workouts imported from TrainingPeaks.

```sql
CREATE TABLE workouts (
    id INTEGER PRIMARY KEY,
    workout_day TEXT NOT NULL,              -- Date in YYYY-MM-DD format
    workout_title TEXT NOT NULL,            -- Workout name from TrainingPeaks
    workout_data TEXT NOT NULL,             -- JSON: {type, duration, tss, description, ...}
    qualitative_data TEXT,                  -- Legacy field, rarely used
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    athlete_comments TEXT,                  -- Comments from TrainingPeaks
    sequence_number INTEGER DEFAULT 1,      -- For multiple workouts on same day
    fit_file_id INTEGER,                    -- FK to fit_files (nullable)
    proposed_workout_name TEXT              -- Link to proposed workout name
);
```

**Common Queries:**

```python
# Get workouts for a date range
SELECT * FROM workouts
WHERE workout_day >= '2026-01-01' AND workout_day <= '2026-01-07'
ORDER BY workout_day, sequence_number;

# Get workout with FIT file data
SELECT w.*, f.fit_data
FROM workouts w
LEFT JOIN fit_files f ON w.fit_file_id = f.id
WHERE w.id = ?;

# Extract workout type from JSON
SELECT workout_day, workout_title,
       json_extract(workout_data, '$.type') as type,
       json_extract(workout_data, '$.tss') as tss
FROM workouts
WHERE json_extract(workout_data, '$.type') = 'Bike';
```

**workout_data JSON Structure:**

```json
{
  "type": "Bike",
  "duration": 3600,
  "tss": 65,
  "intensity_factor": 0.75,
  "description": "Zone 2 endurance ride with...",
  "distance": 45.2,
  "elevation_gain": 450
}
```

### `fit_files`

Stores parsed FIT file data with intervals and power analysis.

```sql
CREATE TABLE fit_files (
    id INTEGER PRIMARY KEY,
    workout_day TEXT NOT NULL,              -- Date in YYYY-MM-DD format
    workout_title TEXT NOT NULL,            -- Workout name (matched to workouts)
    fit_data TEXT NOT NULL,                 -- JSON: {intervals, power_curve, hr_data, ...}
    file_name TEXT NOT NULL,                -- Original .fit filename
    created_at TIMESTAMP,
    sequence_number INTEGER DEFAULT 1       -- For multiple FIT files on same day
);

CREATE UNIQUE INDEX ux_fit_files_day_title_seq
ON fit_files(workout_day, workout_title, sequence_number);
```

**Common Queries:**

```python
# Get FIT file with intervals
SELECT fit_data FROM fit_files WHERE id = ?;

# Find FIT files without matching workout
SELECT f.* FROM fit_files f
LEFT JOIN workouts w ON f.id = w.fit_file_id
WHERE w.id IS NULL;

# Get all FIT files for a week
SELECT * FROM fit_files
WHERE workout_day >= '2026-01-12' AND workout_day <= '2026-01-18'
ORDER BY workout_day, sequence_number;
```

**fit_data JSON Structure:**

```json
{
  "intervals": [
    {
      "type": "warmup",
      "duration": 600,
      "avg_power": 150,
      "normalized_power": 155,
      "avg_hr": 125,
      "avg_cadence": 85
    },
    {
      "type": "threshold",
      "duration": 900,
      "avg_power": 285,
      "normalized_power": 290,
      "avg_hr": 165,
      "avg_cadence": 92,
      "intensity_factor": 0.95
    }
  ],
  "power_curve": {
    "5": 450,
    "30": 380,
    "60": 350,
    "300": 300,
    "1200": 280
  },
  "total_work": 850000,
  "variability_index": 1.05
}
```

### `workout_analyses`

Stores AI-generated analysis of completed workouts.

```sql
CREATE TABLE workout_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER,                     -- FK to workouts (nullable for standalone FIT)
    fit_file_id INTEGER,                    -- FK to fit_files
    analysis_text TEXT NOT NULL,            -- Human-readable analysis
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_used TEXT,                        -- "claude-3-5-sonnet-20241022" or "gemini-1.5-flash"
    analysis_data TEXT,                     -- JSON: structured interval data
    peak_efforts TEXT,                      -- JSON: {duration: {power, hr}, ...}
    FOREIGN KEY (workout_id) REFERENCES workouts(id),
    FOREIGN KEY (fit_file_id) REFERENCES fit_files(id)
);
```

**Common Queries:**

```python
# Get analysis for a workout
SELECT * FROM workout_analyses WHERE workout_id = ?;

# Get all analyses from last week
SELECT wa.*, w.workout_day, w.workout_title
FROM workout_analyses wa
JOIN workouts w ON wa.workout_id = w.id
WHERE w.workout_day >= date('now', '-7 days');

# Count analyses by model
SELECT model_used, COUNT(*) as count
FROM workout_analyses
GROUP BY model_used;
```

**peak_efforts JSON Format (NEW):**

```json
{
  "5": { "power": 450, "hr": 182 },
  "30": { "power": 380, "hr": 175 },
  "60": { "power": 350, "hr": 172 },
  "300": { "power": 300, "hr": 168 },
  "1200": { "power": 280, "hr": 165 }
}
```

**peak_efforts JSON Format (OLD - still in DB):**

```json
{
  "5": 450,
  "30": 380,
  "60": 350,
  "300": 300,
  "1200": 280
}
```

**Handling Both Formats:**

```python
import json

peak_efforts = json.loads(row['peak_efforts']) if row['peak_efforts'] else {}
for duration, data in peak_efforts.items():
    if isinstance(data, dict):
        power = data.get('power', 0)
        hr = data.get('hr', None)
    else:
        power = data  # Old format: just a number
        hr = None
```

### `weekly_summaries`

AI-generated summaries of training weeks.

```sql
CREATE TABLE weekly_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date TEXT NOT NULL,               -- Monday of the week
    end_date TEXT NOT NULL,                 -- Sunday of the week
    summary_data TEXT NOT NULL,             -- Human-readable weekly summary
    qualitative_data TEXT,                  -- Additional notes/observations
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(start_date, end_date)
);
```

**Common Queries:**

```python
# Get summary for a specific week
SELECT * FROM weekly_summaries
WHERE start_date = '2026-01-12';

# Get last 4 weeks of summaries
SELECT * FROM weekly_summaries
ORDER BY start_date DESC
LIMIT 4;
```

## AI Coaching Tables

### `weekly_plans`

High-level weekly training plans generated by AI coach.

```sql
CREATE TABLE weekly_plans (
    weekNumber INTEGER PRIMARY KEY,         -- Week number (e.g., 61)
    startDate TEXT NOT NULL,                -- Monday date (YYYY-MM-DD)
    plannedTSS_min INTEGER,                 -- Minimum TSS target
    plannedTSS_max INTEGER,                 -- Maximum TSS target
    notes TEXT NOT NULL,                    -- JSON or TEXT: weekly goals, focus areas
    ftp INTEGER                             -- Athlete's FTP at time of plan creation
);
```

**Common Queries:**

```python
# Get current week's plan
SELECT * FROM weekly_plans
WHERE startDate <= date('now') AND date(startDate, '+6 days') >= date('now');

# Get plan by week number
SELECT * FROM weekly_plans WHERE weekNumber = 61;
```

**notes Field (can be JSON or TEXT):**

```json
{
  "weeklyGoals": [
    "Build threshold endurance with 2x15min efforts",
    "Maintain VO2max capacity with 3x5min intervals"
  ],
  "keyWorkouts": ["Tuesday: Threshold Development", "Friday: VO2max Intervals"],
  "recoveryFocus": "Active recovery spins on rest days"
}
```

### `daily_plans`

Individual days within a weekly plan.

```sql
CREATE TABLE daily_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    weekNumber INTEGER NOT NULL,            -- FK to weekly_plans
    dayNumber INTEGER NOT NULL,             -- 1-7 (Monday=1, Sunday=7)
    date TEXT NOT NULL,                     -- YYYY-MM-DD
    FOREIGN KEY (weekNumber) REFERENCES weekly_plans(weekNumber)
);
```

**Common Queries:**

```python
# Get all days for a week
SELECT * FROM daily_plans WHERE weekNumber = 61 ORDER BY dayNumber;

# Get today's plan
SELECT * FROM daily_plans WHERE date = date('now');
```

### `proposed_workouts`

Detailed workout proposals for each day.

```sql
CREATE TABLE proposed_workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dailyPlanId INTEGER NOT NULL,           -- FK to daily_plans
    type TEXT NOT NULL,                     -- "bike", "strength", "mobility"
    name TEXT NOT NULL,                     -- Workout title
    plannedDuration INTEGER,                -- Seconds
    plannedTSS_min INTEGER,
    plannedTSS_max INTEGER,
    targetRPE_min INTEGER,                  -- 1-10 scale
    targetRPE_max INTEGER,
    intervals TEXT,                         -- JSON: interval structure
    sections TEXT,                          -- JSON: alternative format
    notes TEXT,                             -- JSON or TEXT: workout notes
    FOREIGN KEY (dailyPlanId) REFERENCES daily_plans(id),
    UNIQUE(dailyPlanId, name) ON CONFLICT IGNORE
);
```

**Common Queries:**

```python
# Get workouts for a specific day
SELECT pw.* FROM proposed_workouts pw
JOIN daily_plans dp ON pw.dailyPlanId = dp.id
WHERE dp.date = '2026-01-15';

# Get bike workouts for a week
SELECT pw.*, dp.date
FROM proposed_workouts pw
JOIN daily_plans dp ON pw.dailyPlanId = dp.id
WHERE dp.weekNumber = 61 AND pw.type = 'bike'
ORDER BY dp.date;

# Get workouts with intervals for Zwift generation
SELECT pw.intervals, pw.notes, dp.date, pw.name
FROM proposed_workouts pw
JOIN daily_plans dp ON pw.dailyPlanId = dp.id
WHERE dp.date >= '2026-01-12' AND dp.date <= '2026-01-18'
  AND pw.type = 'bike' AND pw.intervals IS NOT NULL;
```

**intervals JSON Structure:**

```json
{
  "warmup": {
    "duration": 600,
    "power": { "min": 0.5, "max": 0.65 },
    "description": "Easy spin to prepare muscles"
  },
  "mainSet": [
    {
      "type": "threshold",
      "duration": 900,
      "power": { "target": 0.95 },
      "cadence": 90,
      "repeat": 2,
      "rest": 300,
      "description": "Hold steady threshold power"
    }
  ],
  "cooldown": {
    "duration": 600,
    "power": { "max": 0.55 },
    "description": "Easy recovery spin"
  }
}
```

## Supporting Tables

### `athlete_settings`

Stores athlete-specific settings like FTP, zones, preferences.

```sql
CREATE TABLE athlete_settings (
    athlete_id TEXT PRIMARY KEY,            -- Default: "default"
    settings_json TEXT,                     -- JSON: all athlete settings
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**settings_json Structure:**

```json
{
  "ftp": 300,
  "weight_kg": 75,
  "max_hr": 185,
  "zones": {
    "z1": [0, 0.55],
    "z2": [0.56, 0.75],
    "z3": [0.76, 0.9],
    "z4": [0.91, 1.05],
    "z5": [1.06, 1.2]
  },
  "trainingpeaks": {
    "athlete_id": "6870291"
  }
}
```

### `personal_bests`

Tracks athlete's personal best efforts across various durations.

```sql
CREATE TABLE personal_bests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id TEXT DEFAULT 'default',
    effort_type TEXT NOT NULL,              -- "power_5s", "power_1min", "hr_20min", etc.
    effort_value REAL NOT NULL,             -- Watts or BPM
    workout_id INTEGER,                     -- FK to workouts (nullable)
    fit_file_id INTEGER,                    -- FK to fit_files (nullable)
    achieved_date TEXT NOT NULL,            -- Date of achievement
    rank INTEGER,                           -- Historical ranking (1=current best)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workout_id) REFERENCES workouts(id),
    FOREIGN KEY (fit_file_id) REFERENCES fit_files(id)
);

CREATE INDEX idx_personal_bests_effort
ON personal_bests(athlete_id, effort_type, effort_value DESC);
```

**Common Queries:**

```python
# Get current personal bests
SELECT * FROM personal_bests
WHERE athlete_id = 'default' AND rank = 1
ORDER BY effort_type;

# Get top 5 power efforts for 5 minutes
SELECT * FROM personal_bests
WHERE athlete_id = 'default' AND effort_type = 'power_300s'
ORDER BY effort_value DESC
LIMIT 5;
```

### `daily_metrics`

Generic storage for daily metrics (sleep, HRV, weight, etc.).

```sql
CREATE TABLE daily_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                     -- YYYY-MM-DD
    metric_type TEXT NOT NULL,              -- "sleep", "hrv", "weight", "rhr", etc.
    metric_data TEXT NOT NULL,              -- JSON: metric details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, metric_type)
);
```

**metric_data Examples:**

```json
// Sleep
{"hours": 7.5, "quality": "good", "hrv": 65}

// Weight
{"kg": 75.2, "trend": "stable"}

// HRV
{"morning_hrv": 68, "resting_hr": 48}
```

## Backup Tables

### `workouts_old`, `fit_files_old`

Legacy tables from previous schema. Not actively used but preserved for data archaeology.

### `daily_plans_backup`, `proposed_workouts_backup`, `workout_performance_backup`

Backup tables created during schema migrations. Can be dropped after verification.

## Data Relationships

```
┌─────────────────┐
│ weekly_plans    │
│ (weekNumber PK) │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐
│  daily_plans    │
│ (id PK)         │
└────────┬────────┘
         │ 1:N
         ▼
┌─────────────────┐       ┌──────────────┐
│proposed_workouts│       │   workouts   │
│ (id PK)         │       │ (id PK)      │
└─────────────────┘       └──────┬───────┘
                                 │ 1:1 (nullable)
                                 ▼
                          ┌──────────────┐
                          │  fit_files   │
                          │ (id PK)      │
                          └──────┬───────┘
                                 │ 1:N
                                 ▼
                          ┌──────────────────┐
                          │workout_analyses  │
                          │ (id PK)          │
                          └──────────────────┘

┌─────────────────┐       ┌──────────────────┐
│athlete_settings │       │ personal_bests   │
│ (athlete_id PK) │       │ (id PK)          │
└─────────────────┘       └──────────────────┘
```

## Common Gotchas

### 1. Column Name: `workout_day` not `workout_date`

```python
# ❌ WRONG
SELECT * FROM workouts WHERE workout_date = '2026-01-15';

# ✅ CORRECT
SELECT * FROM workouts WHERE workout_day = '2026-01-15';
```

### 2. JSON Data Requires json_extract

```python
# ❌ WRONG
SELECT workout_data.type FROM workouts;

# ✅ CORRECT
SELECT json_extract(workout_data, '$.type') as type FROM workouts;
```

### 3. peak_efforts Format Changed

```python
# Handle both old (number) and new ({power, hr}) formats
peak_efforts = json.loads(row['peak_efforts']) if row['peak_efforts'] else {}
for duration, data in peak_efforts.items():
    if isinstance(data, dict):
        power = data.get('power', 0)
        hr = data.get('hr', None)
    else:
        power = data  # Old format
        hr = None
```

### 4. fit_file_id is Nullable

```python
# Always check for None
if workout['fit_file_id']:
    fit_data = get_fit_file(workout['fit_file_id'])
else:
    # No FIT file available for this workout
    pass
```

### 5. Multiple Workouts Same Day

```python
# Use sequence_number to differentiate
SELECT * FROM workouts
WHERE workout_day = '2026-01-15'
ORDER BY sequence_number;  # Get all workouts in order
```

## Database Access Patterns

### Using WorkoutDatabase Class

```python
from src.storage.database import WorkoutDatabase

db = WorkoutDatabase()

# ❌ DON'T access db.conn directly
cursor = db.conn.cursor()

# ✅ DO use the database methods
workouts = db.get_workouts_for_date_range(start_date, end_date)
fit_file = db.get_fit_file(fit_file_id)
analysis = db.get_workout_analysis(workout_id)
```

### Transaction Safety

```python
try:
    db.conn.execute("BEGIN TRANSACTION")
    db.conn.execute("INSERT INTO workouts ...")
    db.conn.execute("INSERT INTO fit_files ...")
    db.conn.commit()
except Exception as e:
    db.conn.rollback()
    raise
```

## Indexes and Performance

**Existing Indexes:**

- `ux_workouts_day_title_seq` - Ensures unique workouts per day
- `ux_fit_files_day_title_seq` - Ensures unique FIT files per day
- `idx_personal_bests_effort` - Fast lookups for personal bests

**Recommended Queries Use Indexes:**

```sql
-- Fast (uses index)
SELECT * FROM workouts WHERE workout_day = '2026-01-15';

-- Slow (no index on created_at)
SELECT * FROM workouts WHERE created_at > '2026-01-01';

-- Fast (uses index)
SELECT * FROM personal_bests
WHERE athlete_id = 'default' AND effort_type = 'power_300s';
```

## Schema Evolution

**Adding New Columns:**

```sql
-- Safe: adds nullable column
ALTER TABLE workouts ADD COLUMN new_field TEXT;

-- Safe: adds column with default
ALTER TABLE workouts ADD COLUMN new_counter INTEGER DEFAULT 0;
```

**Modifying Existing Columns:**
SQLite doesn't support ALTER COLUMN, so:

1. Create new table with desired schema
2. Copy data with transformation
3. Drop old table
4. Rename new table
5. Recreate indexes

**Migration Example:**

```python
# Create backup
db.conn.execute("CREATE TABLE workouts_backup AS SELECT * FROM workouts")

# Create new table
db.conn.execute("""
    CREATE TABLE workouts_new (
        id INTEGER PRIMARY KEY,
        -- new schema here
    )
""")

# Copy data with transformation
db.conn.execute("""
    INSERT INTO workouts_new
    SELECT id, workout_day, ... FROM workouts
""")

# Swap tables
db.conn.execute("DROP TABLE workouts")
db.conn.execute("ALTER TABLE workouts_new RENAME TO workouts")
```

## Next Steps

- **Query Optimization**: [api-endpoints.md](./api-endpoints.md) - See how API queries use this schema
- **Data Flow**: [../agent-instructions/getting-started.md](../agent-instructions/getting-started.md#understanding-the-data-flow) - Understand how data moves through the system
- **Testing Queries**: Test database queries before integrating into code using `sqlite3 data/fitness_data.db`
