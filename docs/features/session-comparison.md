# Session Comparison Feature - Implementation Summary

**Feature:** Session Comparison Tool  
**Status:** ✅ Complete  
**Date Completed:** January 2, 2026

---

## Overview

The Session Comparison Tool allows you to find similar workouts from your training history and compare them side-by-side to track progress, identify improvements, and understand fitness development over time.

## Features Implemented

### 1. Similarity Algorithm (`src/utils/workout_comparator.py`)

**WorkoutComparator Class:**

- `calculate_similarity_score()` - Calculates 0-100 similarity score between workouts
- `find_similar_workouts()` - Finds top N most similar workouts
- `compare_workouts_detailed()` - Generates comprehensive comparison metrics

**Similarity Factors** (weighted scoring):

- TSS Similarity: 30% weight
- Duration Similarity: 25% weight
- Interval Structure: 25% weight (count & duration of work intervals)
- Power Zone Distribution: 20% weight

### 2. UI Components (`src/ui/components/session_comparison.py`)

**Display Functions:**

- `display_session_comparison()` - Side-by-side workout comparison
- `display_similar_workouts_list()` - Scrollable list of similar sessions
- `display_power_curve_overlay()` - Overlaid power curves for visual comparison
- `display_find_similar_ui()` - Search interface with filters

**Comparison Display Includes:**

- Key metrics comparison (TSS, duration, distance)
- Interval execution comparison (power, HR)
- Power curve overlay (if FIT data available)
- Improvement highlights

### 3. API Endpoint (`src/api/app.py`)

**New Endpoint:**

```
GET /workouts/with-analyses
```

Returns all workouts with their analyses and interval data for comparison.

### 4. UI Integration (`src/ui/streamlit_app.py`)

**New Navigation Page:**

- 🔄 Session Comparison (added to sidebar)
- `display_session_comparison_page()` function

**Two Comparison Modes:**

1. **Find Similar Workouts** - Automatic similarity search

   - Select target workout
   - Adjust similarity threshold (30-90%)
   - Shows ranked list of similar sessions
   - Displays detailed comparison with top match

2. **Compare Two Specific Workouts** - Manual selection
   - Choose any two workouts
   - View detailed comparison
   - See similarity score

## Testing

**Test File:** `tests/test_workout_comparison.py`

**Test Coverage:**

- ✅ Identical workouts (should get ~100% similarity)
- ✅ Very different workouts (should get low similarity)
- ✅ Finding similar workouts from candidates
- ✅ Detailed comparison metrics
- ✅ Interval structure comparison

**Test Results:** 5/5 passing

## Usage

### Prerequisites

1. Have cycling workouts in database
2. Run batch sync to generate analyses with interval detection
3. Ensure FastAPI server is running

### Finding Similar Workouts

1. Navigate to **🔄 Session Comparison** in sidebar
2. Select **🔍 Find Similar Workouts** mode
3. Choose a workout to find matches for
4. Adjust similarity threshold (default: 50%)
5. Set max results (default: 5)
6. Click **🔎 Find Similar Workouts**
7. View ranked list and detailed comparison

### Comparing Specific Workouts

1. Navigate to **🔄 Session Comparison** in sidebar
2. Select **⚖️ Compare Two Specific Workouts** mode
3. Choose Workout 1 (typically more recent)
4. Choose Workout 2 (comparison/historical)
5. Click **⚖️ Compare Workouts**
6. View detailed comparison

## Comparison Metrics

### Basic Metrics

- TSS (Training Stress Score)
- Duration (minutes)
- Distance (if available)
- Change absolute & percentage

### Interval Analysis

- Work interval count
- Average work power
- Average work HR
- Change in power/HR efficiency

### Improvements Identified

- Higher training load
- Stronger intervals
- Improved cardiovascular efficiency
- Better power-to-HR ratio

### Visual Elements

- Overlaid power curves
- Metric cards with delta indicators
- Similarity progress bars
- Color-coded improvements

## Example Use Cases

### 1. Track VO2max Progression

Find all similar VO2max sessions (4x4min @ 350W) and compare:

- Power consistency across sessions
- HR drift over time
- Recovery quality between intervals

### 2. Threshold Development

Compare 2x20min threshold sessions:

- Sustained power improvements
- HR efficiency gains
- Pacing quality

### 3. Race Preparation

Compare similar race-intensity workouts:

- Peak power capabilities
- Fatigue resistance
- Recovery patterns

### 4. Training Block Assessment

Find all similar sessions within a training block:

- Progressive overload verification
- Adaptation tracking
- Deload effectiveness

## Technical Details

### Similarity Score Calculation

```python
# Weighted average of factors:
similarity = (
    tss_similarity * 0.30 +
    duration_similarity * 0.25 +
    interval_similarity * 0.25 +
    zone_similarity * 0.20
)
```

### Interval Structure Comparison

```python
# Compares:
- Work interval count (±20 points per interval difference)
- Average interval duration (percent difference)
- Interval types (vo2max, threshold, tempo, etc.)
```

### Power Curve Overlay

- Plots both workouts on same time axis
- Recent workout: solid line (blue)
- Comparison workout: dashed line (orange)
- Hover shows exact power values
- Time normalized to minutes

## Integration with Existing Features

**Works with:**

- ✅ Automatic Interval Detection (Feature 1)
- ✅ AI Analysis (uses analysis_data)
- ✅ Historical Analysis tab
- ✅ Batch Sync & Analysis

**Requires:**

- Workouts in database
- workout_analyses records
- Interval detection completed

## Future Enhancements (Not Implemented)

Potential improvements for future iterations:

1. Power zone distribution comparison (more detailed)
2. Cadence pattern comparison
3. HR zone distribution comparison
4. Mean maximal power curve comparison
5. Save favorite comparisons
6. Comparison history/bookmarks
7. Export comparison reports
8. Multi-workout comparison (3+ workouts)
9. Training block comparisons
10. Progressive overload tracking charts

## Files Modified/Created

### Created:

- `src/utils/workout_comparator.py` (350 lines)
- `src/ui/components/session_comparison.py` (310 lines)
- `tests/test_workout_comparison.py` (220 lines)
- `SESSION_COMPARISON_FEATURE.md` (this file)

### Modified:

- `src/ui/streamlit_app.py`
  - Added "🔄 Session Comparison" to navigation
  - Added `display_session_comparison_page()` function (160 lines)
- `src/api/app.py`
  - Added `/workouts/with-analyses` endpoint (35 lines)

**Total Lines Added:** ~1,075 lines

## Notes

- The similarity algorithm weights can be adjusted in `workout_comparator.py`
- Minimum similarity threshold can be user-adjusted (30-90%)
- Power curve overlay requires FIT file data (power_series)
- Works best with structured workouts (intervals detected)
- Non-cycling workouts are filtered out automatically

## Success Criteria

✅ **All Met:**

- Calculate similarity scores between workouts
- Find top N similar workouts from history
- Display side-by-side comparison
- Show metric changes with delta indicators
- Overlay power curves for visual comparison
- Identify key improvements
- Test coverage (5/5 passing)
- User-friendly UI with two modes
- Integrated with existing features
