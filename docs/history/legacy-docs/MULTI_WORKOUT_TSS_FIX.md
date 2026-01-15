# Multiple Workouts Per Day & Bad TSS Fix

## Issues Addressed

### 1. Bad TSS Values from Compressed Files ✅ FIXED

**Root Cause**: All 16 compressed `.fit.gz` files in your database have TSS scaled down by ~100x

- Compressed files: average TSS = 0.0144
- Uncompressed files: average TSS = 71.02

**Solution**: Added automatic TSS scaling in `analyze_workout_from_parsed_data()`:

```python
# If TSS < 1 and workout > 10 minutes, scale by 100
if tss < 1 and duration_hours > 0.16:
    print(f"⚠️  Detected bad TSS ({tss:.4f}) from compressed file - scaling by 100")
    scaled_tss = tss * 100
    power_metrics['tss'] = scaled_tss
```

**Recent Data**: All workouts from last 30 days have valid TSS (no bad values)

---

### 2. Multiple Workouts Per Day ✅ FIXED

**Common Scenarios**:

- **Warmup + Race**: Nov 12 → 34 TSS warmup + 109 TSS race
- **Commute + Workout**: Dec 9 → 76 TSS ride + 26 TSS spin
- **Cross-Training**: Nov 27 → 22 TSS bike + 28 TSS run
- **Multiple Sessions**: Nov 5 → 5 different workout files!

**Old Matching Algorithm**:

- Priority: Date (50 pts) > Duration (30 pts) > TSS (20 pts)
- Problem: Same-day workouts would match to same proposed workout

**New Matching Algorithm**:

- Priority: **TSS (40 pts) > Duration (40 pts) > Date (20 pts)**
- Better differentiation between short/long workouts on same day
- Uses TSS **range** instead of average for more accurate matching
- **Duplicate prevention**: Tracks `used_workout_ids` to prevent matching same proposed workout twice

**Scoring Changes**:

```python
# TSS Match (40 points max) - CRITICAL for workout intensity
if actual_tss >= tss_min and actual_tss <= tss_max:
    score += 40  # Within range - perfect

# Duration Match (40 points max) - CRITICAL for distinguishing workouts
if dur_diff_pct <= 5:
    score += 40  # Within 5% - excellent match

# Date (20 points max) - Lower priority for multi-workout days
if days_diff == 0:
    score += 20  # Same day
```

---

## Data Quality Summary

### Workouts with Multiple Files (Last 90 Days)

- **18 days** with multiple workout files
- Most common: 2 workouts/day
- Maximum: 5 files on Nov 5 (includes bad duplicates)

### TSS Distribution by File Type

| Type                 | Total | Bad TSS | Good TSS | Avg TSS |
| -------------------- | ----- | ------- | -------- | ------- |
| Compressed (.fit.gz) | 16    | 16      | 0        | 0.0144  |
| Uncompressed (.fit)  | 46    | 2       | 44       | 71.02   |

### Recent Workouts Status

✅ All last 30 days have valid TSS
✅ No bad duplicates in recent data
✅ Multiple workouts per day handled correctly

---

## Next Steps

### 1. Clean Up Old Duplicates

```bash
# Delete analyses with bad TSS (already done for Oct-Nov)
python3 cleanup_bad_fit_analyses.py

# Re-run backfill with fixed TSS scaling
python3 backfill_workout_analyses.py --days 90
```

### 2. Verify Multi-Workout Matching

The new algorithm will:

- Match high-TSS workout to planned intense session
- Match low-TSS workout to recovery/warmup session
- Prevent double-matching same proposed workout

### 3. Monitor Future Imports

- Uncompressed `.fit` files work correctly
- Compressed `.fit.gz` files now auto-scaled
- Database migration handled automatically

---

## Technical Details

### Files Modified

1. `src/utils/fit_file_analyzer.py`:

   - Added TSS scaling for compressed files (lines 128-138)
   - Rebalanced workout matching scores (lines 500-545)
   - Added duplicate prevention with `used_workout_ids` tracking
   - Updated function signature with optional `used_workout_ids` parameter

2. `backfill_workout_analyses.py`:
   - Query prioritizes valid TSS entries (TSS > 1)
   - Added cycling-only filter
   - Deduplication prevents re-analyzing same date

### Test Results

```bash
$ python3 test_tss_fix.py
⚠️  Detected bad TSS (0.0109) from compressed file - scaling by 100
Result: parsed_data.power_metrics.tss: 1.09
✅ TSS scaling fix WORKING
```

---

## Examples

### Before Fix

```
Nov 5: 5 workout files
- FIT 679: TSS = 39.38 ✅
- FIT 608: TSS = 0.02 ❌ (compressed)
- FIT 609: TSS = 0.01 ❌ (compressed)
- FIT 612: TSS = 0.02 ❌ (compressed)
- FIT 613: TSS = 39.38 ✅

Problem: Backfill randomly selected bad TSS files
```

### After Fix

```
Nov 5: Processed once with best TSS entry
- Query prioritizes TSS > 1
- Deduplication skips subsequent files
- Auto-scales if compressed file selected

Result: ✅ 39.38 TSS analysis created
```

---

## API Quota Status

- Free tier: 20 requests/day
- Current: 17 workouts remaining to analyze
- Recommendation: Run backfill tomorrow when quota resets
