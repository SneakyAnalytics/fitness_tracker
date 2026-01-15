# Data Processing Pipeline

**Complete guide to how workout data flows through the system.**

## Table of Contents

- [Overview](#overview)
- [FIT File Parser](#fit-file-parser)
- [Interval Detection](#interval-detection)
- [Workout Analysis (AI)](#workout-analysis-ai)
- [Zwift Workout Generation](#zwift-workout-generation)
- [Data Flow Diagram](#data-flow-diagram)
- [Common Usage Patterns](#common-usage-patterns)

---

## Overview

The data processing pipeline transforms raw workout files into actionable insights and future workout plans. This happens in 4 stages:

```
┌────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│ FIT File   │ -> │   Parsed     │ -> │  Intervals  │ -> │     AI       │
│ (.fit)     │    │   Metrics    │    │  Detected   │    │  Analysis    │
└────────────┘    └──────────────┘    └─────────────┘    └──────────────┘
                                                                   │
                                                                   v
┌────────────┐    ┌──────────────┐                      ┌─────────────┐
│  Zwift     │ <- │    Workout   │  <----- AI Coach <-- │  Database   │
│ Workout    │    │     Plan     │                       │  Storage    │
│ (.zwo)     │    │    (JSON)    │                       └─────────────┘
└────────────┘    └──────────────┘
```

**Why this pipeline?**

1. **FIT files** are binary and complex → Need parser to extract metrics
2. **Raw metrics** have noise → Need interval detection to find structure
3. **Numbers alone** don't tell the story → Need AI to create insights
4. **Future training** needs structure → Generate Zwift workouts from plans

---

## FIT File Parser

**File:** [`src/utils/fit_parser.py`](../../src/utils/fit_parser.py)  
**Purpose:** Parse binary FIT files from Garmin/Wahoo/etc into usable metrics

### What it Does

Extracts power, heart rate, cadence, GPS data and calculates:

- **Training zones** (power and HR)
- **Training Stress Score (TSS)**
- **Normalized Power (NP)**
- **Intensity Factor (IF)**
- **Time in zones**

### Key Features

#### 1. Zone Calculation

```python
parser = FitParser()
hr_zones = parser.calculate_hr_zones(hr_data, max_hr=190)
# Returns: {'Zone 1 (Recovery)': 45.2, 'Zone 2 (Endurance)': 40.1, ...}

power_zones = parser.calculate_power_zones(power_data, ftp=250)
# Returns: {'Zone 1 (Recovery)': 10.5, 'Zone 2 (Endurance)': 65.3, ...}
```

**Customization:** Override zones via environment variables:

```bash
export ATHLETE_HR_ZONES="138,156,165,173,200"  # Zone 1 max, Zone 2 max, ...
export ATHLETE_POWER_ZONES="137,187,225,262,300"  # Same format for power
```

#### 2. TSS Calculation

```python
tss = parser.calculate_tss(
    normalized_power=210,
    duration_hours=1.5,
    ftp=250
)
# Returns: 84.67 (Training Stress Score)
```

**Formula:** `TSS = (duration_seconds × NP × IF) / (FTP × 3600) × 100`  
where `IF = NP / FTP`

#### 3. Complete Parsing

```python
with open('workout.fit', 'rb') as f:
    fit_bytes = f.read()

parsed_data = parser.parse_fit_file(fit_bytes, athlete_ftp=250)
```

**Returns:**

```python
{
    'workout_date': '2026-01-14',
    'start_time': '2026-01-14T08:30:00',
    'duration_sec': 5400,  # 90 minutes
    'distance_km': 35.2,
    'elevation_gain_m': 420,

    # Power metrics
    'power_avg': 185,
    'power_max': 345,
    'power_np': 195,
    'if': 0.78,
    'tss': 87.3,
    'power_zones': {...},
    'power_series': [150, 152, 155, ...],  # Second-by-second data

    # Heart rate metrics
    'hr_avg': 142,
    'hr_max': 172,
    'hr_zones': {...},
    'hr_series': [120, 122, 125, ...],

    # Cadence
    'cadence_avg': 88,
    'cadence_series': [85, 87, 88, ...],

    # GPS (if available)
    'latitude_series': [...],
    'longitude_series': [...],
    'altitude_series': [...]
}
```

### Common Issues

**Issue:** TSS calculation seems wrong  
**Cause:** FTP not set or incorrect  
**Fix:** Pass correct `athlete_ftp` parameter

**Issue:** Zones don't match athlete's actual zones  
**Cause:** Using default zone boundaries  
**Fix:** Set `ATHLETE_HR_ZONES` and `ATHLETE_POWER_ZONES` environment variables

**Issue:** Missing power data  
**Cause:** Workout recorded without power meter  
**Fix:** Parser handles gracefully, returns `None` for power metrics

---

## Interval Detection

**File:** [`src/utils/interval_detector.py`](../../src/utils/interval_detector.py)  
**Purpose:** Automatically detect intervals in workout data (no manual tagging needed)

### Algorithm Overview

```
Raw Power Data → Rolling Averages → Zone Classification → State Detection → Intervals
```

**Steps:**

1. **Smooth data** with 30-second rolling window
2. **Classify** each window into training zone (Z1-Z6)
3. **Detect transitions** (rest → work, work → rest)
4. **Group** consecutive periods into intervals
5. **Filter** out noise (too-short intervals)

### Usage

```python
from src.utils.interval_detector import IntervalDetector

detector = IntervalDetector(ftp=250, weight_kg=70)

# Detect from power series
intervals = detector.detect_intervals(
    power_data=[150, 152, 155, ..., 245, 248, ...],
    hr_data=[120, 122, 125, ..., 165, 168, ...],  # Optional
    cadence_data=[85, 87, 88, ...]  # Optional
)
```

**Returns:**

```python
[
    Interval(
        id=1,
        type='warmup',
        start_time=0,
        end_time=600,  # 10 minutes
        duration_sec=600,
        avg_power=150,
        normalized_power=155,
        max_power=180,
        avg_hr=125,
        max_hr=135,
        avg_cadence=85,
        intensity_zone='Z2',
        percent_ftp=0.60
    ),
    Interval(
        id=2,
        type='work',
        start_time=600,
        end_time=900,  # 5 minute interval
        duration_sec=300,
        avg_power=245,
        normalized_power=248,
        max_power=260,
        avg_hr=165,
        max_hr=172,
        avg_cadence=92,
        intensity_zone='Z4',
        percent_ftp=0.98
    ),
    # ... more intervals
]
```

### Training Zones

Based on **Coggan Power Zones**:

- **Z1 (Recovery):** 0-55% FTP
- **Z2 (Endurance):** 56-75% FTP
- **Z3 (Tempo):** 76-90% FTP
- **Z4 (Threshold):** 91-105% FTP
- **Z5 (VO2max):** 106-120% FTP
- **Z6 (Anaerobic):** 120%+ FTP

### Configuration

```python
detector = IntervalDetector(ftp=250)

# Adjust detection parameters
detector.window_size = 30  # Rolling window (seconds)
detector.min_work_duration = 30  # Min interval length (seconds)
detector.min_rest_duration = 20  # Min rest length (seconds)
detector.work_threshold_zone = 'Z3'  # Min zone for "work" intervals
```

### Interval Types

- **warmup:** First 10+ minutes below Z3
- **work:** Z3+ efforts lasting 30+ seconds
- **rest:** Recovery between work intervals
- **cooldown:** Final 5+ minutes below Z3
- **steady_state:** Sustained Z2/Z3 (endurance rides)

### Common Patterns

**Pattern 1: Threshold Intervals**

```python
# Detects: 5x8min @ threshold with 3min rests
intervals = detector.detect_intervals(power_data)
work_intervals = [i for i in intervals if i.type == 'work']
# Returns: 5 intervals, ~8 minutes each, Z4 intensity
```

**Pattern 2: VO2max Workout**

```python
# Detects: 4x4min @ 110% FTP with 4min rests
intervals = detector.detect_intervals(power_data)
vo2_intervals = [i for i in intervals if i.intensity_zone == 'Z5']
# Returns: 4 intervals, ~4 minutes each
```

**Pattern 3: Endurance Ride**

```python
# Detects: 90min @ Z2
intervals = detector.detect_intervals(power_data)
steady = [i for i in intervals if i.type == 'steady_state']
# Returns: 1 long interval, Z2 intensity
```

### Advanced: Custom Classification

```python
# Override zone classification
def custom_classifier(power, ftp):
    percent = power / ftp
    if percent < 0.6:
        return 'recovery'
    elif percent < 0.85:
        return 'endurance'
    elif percent < 1.0:
        return 'tempo'
    else:
        return 'hard'

detector.classify_zone = custom_classifier
```

---

## Workout Analysis (AI)

**File:** [`src/utils/fit_file_analyzer.py`](../../src/utils/fit_file_analyzer.py)  
**Purpose:** Use AI (Gemini) to generate workout insights and detect personal bests

### What it Does

Combines metrics + intervals + athlete context → AI-generated insights:

- **Effort analysis** (how hard was it? sustainable?)
- **Performance trends** (improving? plateauing?)
- **Personal bests** (new power records?)
- **Recovery assessment** (ready for next workout?)
- **Tactical feedback** (pacing, interval execution)

### Usage

```python
from src.utils.fit_file_analyzer import FitFileAnalyzer

analyzer = FitFileAnalyzer()

# Analyze from FIT file bytes
with open('workout.fit', 'rb') as f:
    result = analyzer.analyze_workout(
        fit_file_content=f.read(),
        athlete_ftp=250,
        athlete_notes="Felt strong today, legs felt fresh"
    )
```

**Returns:**

```python
{
    # All parsed metrics (from FIT parser)
    'workout_date': '2026-01-14',
    'duration_sec': 5400,
    'power_avg': 185,
    'tss': 87.3,
    # ... etc

    # AI-generated analysis
    'ai_analysis': """
    Strong threshold session with excellent power consistency.

    Key Observations:
    - Maintained 245w (98% FTP) for 4x8min intervals
    - Heart rate drift minimal (<5bpm across intervals)
    - Recovery intervals well-executed at 150w

    Performance Trends:
    - 8min power improved 5w vs 3 weeks ago
    - TSS accumulation on track (87 vs target 85)

    Personal Bests:
    - 8min: 245w (new PR, +5w)
    - 20min: 235w (matches recent best)

    Recovery: Moderate fatigue expected. Plan 24-48hr before next intensity.
    """,

    # Structured personal bests
    'personal_bests': [
        {
            'duration': '8min',
            'power': 245,
            'previous_best': 240,
            'improvement': 5,
            'date_achieved': '2026-01-14'
        },
        # ... more PRs
    ]
}
```

### Dynamic Model Selection

Analyzer automatically tries multiple Gemini models for resilience:

```python
# Default: Dynamic model discovery
analyzer = FitFileAnalyzer(use_dynamic_models=True)
# Tries: gemini-2.0-flash-exp, gemini-1.5-flash-002, etc.

# Fallback: Static model list
analyzer = FitFileAnalyzer(use_dynamic_models=False)
# Uses: gemini-1.5-flash-002, gemini-1.5-flash, etc.
```

**Why?** Gemini models can become unavailable, change, or reach rate limits. Dynamic discovery ensures the analyzer always finds a working free model.

### Integration with Intervals

```python
# Combine interval detection + AI analysis
detector = IntervalDetector(ftp=250)
intervals = detector.detect_intervals(power_data)

analyzer = FitFileAnalyzer()
result = analyzer.analyze_workout_from_parsed_data(
    parsed_data={
        **parsed_data,
        'detected_intervals': intervals
    }
)
# AI uses interval structure in analysis
```

### Prompt Engineering

The analyzer uses carefully crafted prompts:

1. **System context:** Define AI's role as cycling coach
2. **Metrics context:** Provide all workout data
3. **Historical context:** Include recent training (if available)
4. **Specific instructions:** Ask for structured output

**Example prompt structure:**

```
You are an expert cycling coach analyzing workout data.

Workout Metrics:
- Duration: 90 minutes
- TSS: 87
- Power: 185w avg, 245w for intervals
- Detected Intervals: [4x8min @ Z4, ...]

Recent Training:
- 7-day TSS: 485 (target: 500)
- Last hard workout: 3 days ago

Analyze:
1. Effort sustainability
2. Interval execution quality
3. Performance vs recent workouts
4. Recovery recommendations
5. Personal bests (if any)
```

---

## Zwift Workout Generation

**File:** [`src/utils/zwift_workout_generator.py`](../../src/utils/zwift_workout_generator.py)  
**Purpose:** Generate Zwift-compatible .zwo workout files from JSON workout plans

### What it Does

Converts AI-generated workout plans into Zwift workouts you can ride on the trainer.

**Input:** JSON workout plan  
**Output:** `.zwo` XML file for Zwift

### Usage

```python
from src.utils.zwift_workout_generator import generate_zwift_workout

# Define intervals
intervals = [
    {
        'name': 'Warmup',
        'duration': 600,  # seconds
        'power_target': {'type': 'percent_ftp', 'value': 50}
    },
    {
        'name': 'Threshold Interval',
        'duration': 480,  # 8 minutes
        'power_target': {'type': 'percent_ftp', 'value': 98},
        'repeat': 4,
        'rest': {
            'duration': 180,
            'power_target': {'type': 'percent_ftp', 'value': 60}
        }
    },
    {
        'name': 'Cooldown',
        'duration': 600,
        'power_target': {'type': 'percent_ftp', 'value': 50}
    }
]

# Generate .zwo file
filepath = generate_zwift_workout(
    workout_date='2026-01-15',
    workout_name='Threshold Development',
    intervals=intervals,
    description='4x8min @ 98% FTP with 3min rests',
    ftp=250,
    output_dir='Week_52'
)
# Returns: 'Week_52/2026_01_15_Threshold_Development.zwo'
```

### Power Target Formats

The generator supports multiple formats:

**Format 1: Percent FTP**

```python
{'type': 'percent_ftp', 'value': 85}  # 85% of FTP
```

**Format 2: Watts**

```python
{'type': 'watts', 'value': 210}  # 210 watts absolute
```

**Format 3: Range**

```python
{
    'type': 'range',
    'min': 200,
    'max': 220,
    'unit': 'watts'
}
# Zwift displays range, you control exact power
```

**Format 4: Direct min/max**

```python
{
    'min': 85,
    'max': 95,
    'unit': 'percent_ftp'
}
```

### Interval Types

**1. Steady State**

```python
{
    'name': 'Zone 2 Endurance',
    'duration': 3600,  # 60 minutes
    'power_target': {'type': 'percent_ftp', 'value': 65}
}
```

**2. Repeating Intervals**

```python
{
    'name': 'VO2max',
    'duration': 240,  # 4 minutes
    'power_target': {'type': 'percent_ftp', 'value': 110},
    'repeat': 5,
    'rest': {
        'duration': 240,
        'power_target': {'type': 'percent_ftp', 'value': 55}
    }
}
```

**3. Ramp/Buildup**

```python
{
    'name': 'Warmup Ramp',
    'type': 'ramp',
    'duration': 600,
    'power_start': {'type': 'percent_ftp', 'value': 40},
    'power_end': {'type': 'percent_ftp', 'value': 65}
}
```

**4. Free Ride**

```python
{
    'name': 'Cool Down',
    'type': 'freeride',
    'duration': 300
}
```

### Dynamic Text Alerts

Workouts include entertaining in-ride messages:

```python
# Automatically generated based on context
"💪 Interval 2/4 - You're crushing it!"
"🔥 Final interval! Leave nothing in the tank!"
"😅 Halfway through this suffer-fest. Breathe!"
```

**Customize:**

```python
from src.utils.dynamic_workout_content import dynamic_content

# Add custom messages
dynamic_content.content['interval_start'].append(
    "Your custom motivational message here!"
)
```

### Complete Example

```python
# Full workout generation from AI plan
workout_plan = {
    'date': '2026-01-15',
    'title': 'Sweet Spot Development',
    'description': 'Build sustainable power at 88-94% FTP',
    'target_tss': 85,
    'intervals': [
        {
            'name': 'Warmup',
            'duration': 600,
            'power_target': {'type': 'percent_ftp', 'value': 50}
        },
        {
            'name': 'Sweet Spot',
            'duration': 900,  # 15 minutes
            'power_target': {
                'type': 'range',
                'min': 88,
                'max': 94,
                'unit': 'percent_ftp'
            },
            'repeat': 3,
            'rest': {
                'duration': 300,
                'power_target': {'type': 'percent_ftp', 'value': 60}
            }
        },
        {
            'name': 'Cooldown',
            'duration': 600,
            'power_target': {'type': 'percent_ftp', 'value': 50}
        }
    ]
}

filepath = generate_zwift_workout(
    workout_date=workout_plan['date'],
    workout_name=workout_plan['title'],
    intervals=workout_plan['intervals'],
    description=workout_plan['description'],
    ftp=250,
    output_dir='Week_52',
    week_number=52
)

# Upload to Zwift via their web interface
# Or place in: Documents/Zwift/Workouts/[FTP]/
```

### XML Output Structure

Generated .zwo file structure:

```xml
<workout_file>
    <author>AI Cycling Coach</author>
    <name>2026_01_15_Sweet_Spot_Development</name>
    <description>Build sustainable power at 88-94% FTP</description>
    <sportType>bike</sportType>
    <tags>
        <tag name="threshold"/>
        <tag name="intervals"/>
    </tags>
    <workout>
        <Warmup Duration="600" PowerLow="0.50" PowerHigh="0.50"/>
        <IntervalsT Repeat="3" OnDuration="900" OffDuration="300"
                    OnPower="0.88" OffPower="0.60">
            <textevent timeoffset="30" message="Sweet Spot Interval 1/3 - Find your rhythm!"/>
        </IntervalsT>
        <Cooldown Duration="600" PowerLow="0.50" PowerHigh="0.50"/>
    </workout>
</workout_file>
```

---

## Data Flow Diagram

### Complete Pipeline

```
┌─────────────────┐
│   Athlete       │
│   Records       │
│   Workout       │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  FIT File       │  (.fit from Garmin/Wahoo/etc)
│  Upload         │
└────────┬────────┘
         │
         v
┌─────────────────────────────────────────┐
│           FIT Parser                    │
│  • Extract power/HR/cadence series      │
│  • Calculate TSS, NP, IF                │
│  • Compute zone distributions           │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│       Interval Detector                 │
│  • Rolling window analysis              │
│  • Classify zones (Z1-Z6)               │
│  • Detect work/rest transitions         │
│  • Group into intervals                 │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│      AI Workout Analyzer                │
│  • Gemini AI analysis                   │
│  • Performance insights                 │
│  • Personal best detection              │
│  • Recovery recommendations             │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│          Database Storage               │
│  • Parsed metrics (workouts table)      │
│  • AI analysis (workout_analyses)       │
│  • Personal bests (personal_bests)      │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│         AI Coaching Engine              │
│  • Load athlete profile                 │
│  • Analyze recent training              │
│  • Generate workout plan (JSON)         │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│      Zwift Workout Generator            │
│  • Convert JSON → .zwo XML              │
│  • Add dynamic text alerts              │
│  • Calculate interval timing            │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────┐
│   Athlete       │
│   Rides         │
│   Workout       │
└─────────────────┘
```

---

## Common Usage Patterns

### Pattern 1: Upload & Analyze Workout

```python
from src.utils.fit_parser import FitParser
from src.utils.interval_detector import IntervalDetector
from src.utils.fit_file_analyzer import FitFileAnalyzer
from src.storage.database import WorkoutDatabase

# 1. Parse FIT file
parser = FitParser()
with open('workout.fit', 'rb') as f:
    parsed = parser.parse_fit_file(f.read(), athlete_ftp=250)

# 2. Detect intervals
detector = IntervalDetector(ftp=250)
intervals = detector.detect_intervals(parsed['power_series'])

# 3. AI analysis
analyzer = FitFileAnalyzer()
result = analyzer.analyze_workout_from_parsed_data(
    {**parsed, 'detected_intervals': intervals},
    athlete_ftp=250
)

# 4. Save to database
db = WorkoutDatabase()
db.store_workout_analysis(result)
```

### Pattern 2: Generate Next Week's Workouts

```python
from src.utils.ai_coach_engine import AICoachEngine
from src.utils.zwift_workout_generator import generate_zwift_workout

# 1. AI coaching analysis
coach = AICoachEngine()
result = coach.generate_weekly_plan(
    start_date='2026-01-20',
    athlete_id=1
)

# 2. Generate Zwift files for each workout
for workout in result.workout_plan['workouts']:
    if workout['type'] == 'bike':
        generate_zwift_workout(
            workout_date=workout['date'],
            workout_name=workout['title'],
            intervals=workout['intervals'],
            description=workout['description'],
            ftp=250,
            output_dir=f"Week_{result.workout_plan['week_number']}"
        )
```

### Pattern 3: Batch Process Historical Workouts

```python
import glob
from pathlib import Path

# Process all FIT files in a directory
fit_files = glob.glob('data/fit_files/*.fit')

analyzer = FitFileAnalyzer()
db = WorkoutDatabase()

for fit_path in fit_files:
    with open(fit_path, 'rb') as f:
        result = analyzer.analyze_workout(
            f.read(),
            athlete_ftp=250
        )

        if result:
            db.store_workout_analysis(result)
            print(f"✓ Processed {Path(fit_path).name}")
```

### Pattern 4: Compare Planned vs Actual

```python
from src.utils.workout_comparator import WorkoutComparator

comparator = WorkoutComparator()

comparison = comparator.compare_workouts(
    planned_workout_id=123,
    actual_workout_id=456
)

print(f"Adherence: {comparison['adherence_score']}%")
print(f"Power variance: {comparison['power_variance']}w")
print(f"Duration diff: {comparison['duration_diff_min']} minutes")
```

---

## Troubleshooting

### FIT Parser Issues

**Problem:** "No power data found"  
**Solution:** Check if FIT file was recorded with power meter. Use `hr_data` for analysis instead.

**Problem:** TSS calculation returns 0  
**Solution:** Ensure `athlete_ftp` is passed and > 0.

**Problem:** Zones incorrect  
**Solution:** Set `ATHLETE_HR_ZONES` and `ATHLETE_POWER_ZONES` environment variables.

### Interval Detection Issues

**Problem:** Too many tiny intervals detected  
**Solution:** Increase `min_work_duration` and `min_rest_duration`:

```python
detector.min_work_duration = 60  # 1 minute minimum
detector.min_rest_duration = 30  # 30 seconds minimum
```

**Problem:** Missing intervals  
**Solution:** Lower `work_threshold_zone`:

```python
detector.work_threshold_zone = 'Z2'  # Catch tempo efforts
```

**Problem:** Warmup/cooldown not detected  
**Solution:** Ensure workout has 5+ minutes at Z1/Z2 at start/end.

### AI Analysis Issues

**Problem:** "Rate limit exceeded"  
**Solution:** Dynamic model discovery will automatically try next model. Wait 60 seconds and retry.

**Problem:** "No Gemini API key"  
**Solution:** Set `GEMINI_API_KEY` environment variable or pass to constructor.

**Problem:** Analysis quality poor  
**Solution:** Provide `athlete_notes` with context about how workout felt.

### Zwift Generation Issues

**Problem:** .zwo file won't load in Zwift  
**Solution:** Check for special characters in workout name. Use `clean_zwift_text()`.

**Problem:** Power targets incorrect  
**Solution:** Verify FTP value. Check `power_target` format (percent_ftp vs watts).

**Problem:** Intervals too long/short  
**Solution:** Check `duration` is in seconds, not minutes.

---

## Related Documentation

- [Database Schema](./database-schema.md) - Where processed data is stored
- [API Endpoints](./api-endpoints.md) - How to upload/retrieve data via API
- [AI Coaching System](./ai-coaching-system.md) - How AI generates workout plans
- [Development Workflow](../agent-instructions/development-workflow.md) - Testing and debugging

---

**Last Updated:** January 14, 2026  
**Maintainer:** Fitness Tracker Development Team
