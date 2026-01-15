# AI Analysis Improvement - Resolved Issue with Overly Critical Feedback

## Problem Statement

User reported: _"AI analysis seems to be extremely critical of every workout I do... I did the workout prescribed pretty specifically... I would not expect a 4/10 of execution."_

The AI was giving unfairly harsh scores (4/10) and misinterpreting workout intervals, treating actual work intervals as "failed recovery" and vice versa.

## Root Cause

The AI prompt in `src/utils/fit_file_analyzer.py` had several issues:

1. **Misusing Detected Intervals**: The prompt was comparing execution against time windows from the `.zwo` prescription file, rather than trusting the auto-detected intervals
2. **Inventing Incorrect Prescriptions**: When a prescribed workout existed, the AI was creating an imaginary interval structure that didn't match reality
3. **Harsh Scoring**: The prompt was asking the AI to criticize deviations heavily, rather than being constructive
4. **No Flexibility**: Power execution within ±5-10% of targets (which is normal) was being treated as failures

## Solution Implemented

### 1. Modified AI Prompt to Trust Detected Intervals

- Changed the prompt to explicitly state: _"You must use the AUTO-DETECTED INTERVAL STRUCTURE above as the PRIMARY SOURCE OF TRUTH"_
- Added clear guidelines:
  - Intervals labeled "vo2max" or "threshold" ARE work intervals that were executed
  - Intervals labeled "recovery" or "rest" ARE actual recovery periods at low power
  - DO NOT assume the athlete failed - check detected intervals first

### 2. Added Flexible Scoring Rubric

```
9-10: Exceptional execution, hit all targets, perfect pacing
7-8:  Very good execution, minor deviations (±5-10% power, HR appropriate)
5-6:  Acceptable execution, some struggles but completed core work
3-4:  Significant struggles, major deviations from targets
1-2:  Did not execute the workout as intended, abandoned early
```

### 3. Restructured Analysis Format

Changed from harsh criticism to constructive coaching:

- **EXECUTION SCORE**: Fair scoring based on actual performance
- **WHAT WENT WELL**: Positive reinforcement (2-3 items)
- **INTERVAL EXECUTION QUALITY**: Objective assessment using detected intervals
- **POWER & HEART RATE RELATIONSHIP**: Physiological analysis
- **CONSTRUCTIVE FEEDBACK**: Maximum 1-2 items, actionable and encouraging
- **TRAINING IMPACT & NEXT STEPS**: Forward-looking recommendations

### 4. Removed Problematic Time-Window Analysis

Deleted the `_analyze_prescribed_intervals()` method call that was calculating stats from fixed time windows, which didn't account for:

- Workout modifications by athlete
- Timing delays or early starts
- Athletes adjusting intervals on the fly

## Results Comparison

### Before (OLD PROMPT):

```
Adherence Score: 4/10

The athlete severely missed power targets throughout this workout...
Prescribed: 350-370W, Actual: 263W avg

Recovery 2: 297W - Extreme Overshoot, near 100% FTP! No recovery occurring.
VO2max 1: 182W - Major Miss. Only 61% of target power.

Conclusion: No VO2max stimulus was effectively applied.
```

### After (NEW PROMPT):

```
EXECUTION SCORE: 7/10

You successfully hit the core structure of the workout, achieving a TSS
of 96.4, which is right in our target range (95-105).

WHAT WENT WELL:
1. TSS and Duration Target Hit: You completed the planned 90 minutes
2. High-Quality Opening: The first VO2max effort (352W @ 116% FTP) was
   spot on—nearly 4 minutes executed at precisely the right intensity
3. Recovery Discipline: Your recovery efforts averaged 140-177W, showing
   you were successfully flushing the system

INTERVAL EXECUTION QUALITY:
- Initial Work (Intervals 1 & 2): 352W and 347W, excellent numbers,
  firmly in the VO2max zone (114-116% FTP)
- Later Work: Settled to 305W–317W (Z4). Given this was your first hard
  VO2max session in 12 weeks, a slight drop is expected and smart.
```

## Impact

✅ **Score changed from 4/10 → 7/10** (more accurate)
✅ **Tone changed from harsh → encouraging** (professional coaching)
✅ **Interval interpretation fixed** (work is work, recovery is recovery)
✅ **Constructive feedback** (cadence management, pacing strategy)
✅ **Actionable recommendations** (48h recovery, next workout type)

## Files Modified

1. **`src/utils/fit_file_analyzer.py`**
   - Lines 813-903: Updated prompt for workouts WITH prescribed plan
   - Lines 906-994: Updated prompt for workouts WITHOUT prescribed plan
   - Removed `interval_execution` variable that called `_analyze_prescribed_intervals()`
   - Both prompts now trust detected intervals as source of truth
   - Added clear scoring rubric and analysis structure
   - Emphasis on constructive, encouraging coaching tone

## Testing

Tested with 12/31/2025 VO2max workout:

- **Detected intervals**: 11 intervals (2x vo2max @ 350W, 3x work @ 313W, 4x recovery @ 150W)
- **Actual execution**: User hit VO2max targets at 352W and 347W (114-116% FTP)
- **New analysis**: Correctly identified excellent execution of main intervals
- **Score**: Fair 7/10 reflecting good execution with minor room for improvement
- **Feedback**: Constructive suggestions on cadence (95-105 rpm) and pacing strategy

## User Verification

User can verify the improvement by:

1. Opening Streamlit app (`python3 -m streamlit run src/ui/app.py`)
2. Navigating to Historical Analysis tab
3. Viewing the 12/31/2025 workout analysis
4. Checking the Intervals tab to see detected intervals
5. Reading the AI analysis which should now be:
   - More encouraging and professional
   - Accurate in identifying work vs recovery intervals
   - Fair in scoring (7/10 vs old 4/10)
   - Constructive with actionable feedback

## Next Steps

1. ✅ User should test the updated analysis in the UI
2. ⏳ Monitor future workout analyses to ensure consistent quality
3. ⏳ User may want to re-analyze other recent workouts with improved prompt
4. ⏳ Continue with Feature 2 from Vekta implementation plan (Session Comparison)

## Notes

- The improved prompt maintains the same level of detail and specificity
- It still provides interval-by-interval analysis when appropriate
- Power targets within ±5-10% are now considered "good execution" not "failures"
- The AI now recognizes that athletes often modify workouts slightly (this is normal)
- Recovery recommendations and training impact analysis are still provided
