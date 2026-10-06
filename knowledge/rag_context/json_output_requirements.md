# Weekly Training Plan JSON Format Template

## Purpose

This document defines the exact JSON structure required for Jake's custom fitness application. The application auto-generates Zwift workout files and populates a training calendar based on this format.

## Critical Requirements

1. **Format consistency is MANDATORY** - any deviation breaks the application
2. **FTP value must be included** at the top level for dynamic power calculations
3. **Duration values are in SECONDS** for intervals, MINUTES for workout totals
4. **Power targets** can be specified as ranges (watts), percent FTP, or progressive (start/end)
5. **All date formats** must be YYYY-MM-DD

## ⚠️ CRITICAL: Exercise Structure Requirements

**DO NOT create generic "workout blocks" with multiple movements in notes!**

❌ **WRONG - Generic single exercise:**

```json
{
  "name": "Upper Body Circuit",
  "sets": [
    {
      "notes": ["Push-ups, rows, shoulder press, tricep dips"]
    }
  ]
}
```

✅ **CORRECT - Separate exercise for each movement:**

```json
{
  "name": "Push-ups",
  "sets": [{"reps": "12", "weight": "bodyweight", "rest": 60}]
},
{
  "name": "Dumbbell Rows",
  "sets": [{"reps": "10", "weight": "30 lbs", "rest": 60}]
},
{
  "name": "Shoulder Press",
  "sets": [{"reps": "8", "weight": "25 lbs", "rest": 60}]
}
```

**This applies to ALL workout types: strength, mobility, yoga, etc.**

---

## Top-Level Structure

```json
{
  "weekNumber": <integer>,
  "startDate": "YYYY-MM-DD",
  "ftp": <integer>,
  "plannedTSS": {
    "min": <integer>,
    "max": <integer>
  },
  "notes": {
    "weekFocus": "<string>",
    "specialConsiderations": "<string>"
  },
  "days": [<array of day objects>]
}
```

### Field Descriptions

- **weekNumber**: Sequential week number in training plan (integer)
- **startDate**: Monday's date in YYYY-MM-DD format (string)
- **ftp**: Current Functional Threshold Power in watts (integer) - REQUIRED for Zwift file generation
- **plannedTSS**: Training Stress Score range (object with min/max integers)
- **notes**: Week-level context (object with weekFocus and specialConsiderations strings)
- **days**: Array of 7 day objects (see Day Structure below)

---

## Day Structure

```json
{
  "dayNumber": <1-7>,
  "date": "YYYY-MM-DD",
  "workouts": [<array of workout objects>]
}
```

### Field Descriptions

- **dayNumber**: 1=Monday through 7=Sunday (integer)
- **date**: Specific date in YYYY-MM-DD format (string)
- **workouts**: Array of workout objects (can be multiple per day)

---

## Workout Types

### Type: "bike"

```json
{
  "type": "bike",
  "name": "<descriptive workout name>",
  "plannedDuration": <minutes as integer>,
  "plannedTSS": {
    "min": <integer>,
    "max": <integer>
  },
  "targetRPE": {
    "min": <1-10>,
    "max": <1-10>
  },
  "intervals": [<array of interval objects>],
  "notes": [<array of strings>]
}
```

#### Optional Fields for Outdoor Rides:

```json
{
  "type": "bike",
  "outdoorGuidelines": {
    "routeType": "<string>",
    "terrain": "<string>",
    "focus": "<string>",
    "distance": "<string>"
  },
  "structureGuidelines": {
    "warmup": "<string>",
    "mainBlock": "<string>",
    "cooldown": "<string>"
  },
  "powerGuidelines": {
    "baseEffort": "<string>",
    "hillClimbs": "<string>",
    "technical": "<string>",
    "recovery": "<string>"
  },
  "skillFocus": [<array of strings>]
}
```

---

## Interval Structure (for structured bike workouts)

### Basic Interval Format

```json
{
  "name": "<interval name>",
  "duration": <seconds as integer>,
  "powerTarget": <power target object>,
  "cadenceTarget": {
    "min": <rpm as integer>,
    "max": <rpm as integer>
  }
}
```

### Power Target Options

**Option 1: Range in Watts**

```json
"powerTarget": {
  "type": "range",
  "min": <watts>,
  "max": <watts>,
  "unit": "watts"
}
```

**Option 2: Percent FTP (Progressive)**

```json
"powerTarget": {
  "start": {
    "type": "percent_ftp",
    "value": <percentage as integer>
  },
  "end": {
    "type": "percent_ftp",
    "value": <percentage as integer>
  }
}
```

**Option 3: Fixed Range (shorthand for equal min/max)**

```json
"powerTarget": {
  "type": "range",
  "min": 270,
  "max": 270,
  "unit": "watts"
}
```

---

## Type: "run"

```json
{
  "type": "run",
  "name": "<descriptive run name>",
  "plannedDuration": <minutes as integer>,
  "plannedTSS": {
    "min": <integer>,
    "max": <integer>
  },
  "targetRPE": {
    "min": <1-10>,
    "max": <1-10>
  },
  "notes": [<array of strings>]
}
```

**Note:** Running workouts do NOT use intervals structure - guidance is provided in notes array.

---

## Type: "mobility"

```json
{
  "type": "mobility",
  "name": "<descriptive session name>",
  "plannedDuration": <minutes as integer>,
  "plannedTSS": {
    "min": 0,
    "max": 0
  },
  "targetRPE": {
    "min": 1,
    "max": 2
  },
  "sections": [<array of section objects>]
}
```

### Section Structure

**CRITICAL:** Mobility workouts must list EACH movement/pose as a separate exercise with specific duration. Do NOT list multiple movements in one exercise's notes.

```json
{
  "name": "<section name>",
  "duration": <total section duration in minutes>,
  "exercises": [
    {
      "name": "<specific movement/pose name>",
      "sets": [
        {
          "duration": <seconds for this movement>,
          "perSide": <true if movement is per side (e.g., pigeon pose)>,
          "notes": [
            "<specific cues for THIS movement only>",
            "<form focus points>"
          ]
        }
      ]
    }
  ]
}
```

**Example 30-minute Mobility Session:**

```json
{
  "type": "mobility",
  "name": "Active Recovery - Yoga & Mobility",
  "plannedDuration": 30,
  "sections": [
    {
      "name": "Gentle Flow",
      "duration": 30,
      "exercises": [
        {
          "name": "Cat-Cow",
          "sets": [
            {
              "duration": 120,
              "notes": ["5 breaths", "Focus on spinal articulation"]
            }
          ]
        },
        {
          "name": "Downward Dog",
          "sets": [
            {
              "duration": 180,
              "notes": ["Hold for 3 minutes", "Pedal feet to stretch calves"]
            }
          ]
        },
        {
          "name": "Pigeon Pose",
          "sets": [
            {
              "duration": 300,
              "perSide": true,
              "notes": [
                "5 minutes per side",
                "Deep hip opener",
                "Use props as needed"
              ]
            }
          ]
        },
        {
          "name": "Child's Pose",
          "sets": [
            {
              "duration": 180,
              "notes": ["Rest and breathe", "Arms extended forward"]
            }
          ]
        },
        {
          "name": "Supine Twist",
          "sets": [
            {
              "duration": 240,
              "perSide": true,
              "notes": ["4 minutes per side", "Gentle spinal rotation"]
            }
          ]
        },
        {
          "name": "Savasana",
          "sets": [
            {
              "duration": 300,
              "notes": ["Final relaxation", "Body scan meditation"]
            }
          ]
        }
      ]
    }
  ]
}
```

Note: Exercise durations (120+180+300+300+180+240+240+300 = 1920 seconds ≈ 32 minutes) should approximately match section duration (30 min), accounting for transitions.

---

## Type: "strength"

Used for resistance training, gym sessions, bodyweight workouts, etc.

**CRITICAL REQUIREMENTS:**

1. **MUST use the `sections` structure** with detailed exercises, sets, and reps - NOT simple notes array
2. **Each movement MUST be a separate exercise** - Do NOT list multiple exercises in one exercise's notes
3. **Each exercise MUST have specific sets with reps/weight/rest** - Do NOT use generic descriptions
4. **Example:** Instead of one exercise "Upper Body Circuit" with notes "Push-ups, rows, dips", create THREE separate exercises: "Push-ups" (3x12), "Dumbbell Rows" (3x10), "Tricep Dips" (3x15)

```json
{
  "type": "strength",
  "name": "<descriptive workout name>",
  "plannedDuration": <minutes as integer>,
  "plannedTSS": {
    "min": <integer>,
    "max": <integer>
  },
  "targetRPE": {
    "min": <1-10>,
    "max": <1-10>
  },
  "sections": [<array of section objects>]
}
```

### Strength Section Structure

Each section represents a workout block (warmup, main lifts, accessory work, cooldown).

```json
{
  "name": "<section name>",
  "duration": <minutes as integer>,
  "rounds": <integer (optional)>,
  "exercises": [
    {
      "name": "<exercise name>",
      "sets": [
        {
          "reps": <integer or string like "8-12" or "AMRAP">,
          "weight": <string like "bodyweight", "moderate", "heavy", or specific weight>,
          "rest": <seconds as integer>,
          "notes": [<array of instruction strings>]
        }
      ]
    }
  ]
}
```

### Strength Workout Example

```json
{
  "type": "strength",
  "name": "Full Body Strength - Lower Focus",
  "plannedDuration": 60,
  "plannedTSS": {
    "min": 10,
    "max": 20
  },
  "targetRPE": {
    "min": 6,
    "max": 8
  },
  "sections": [
    {
      "name": "Dynamic Warmup",
      "duration": 10,
      "exercises": [
        {
          "name": "Leg Swings",
          "sets": [
            {
              "reps": "10 each leg",
              "weight": "bodyweight",
              "rest": 0,
              "notes": ["Forward/back and side-to-side", "Loosen hip flexors"]
            }
          ]
        },
        {
          "name": "Bodyweight Squats",
          "sets": [
            {
              "reps": "15",
              "weight": "bodyweight",
              "rest": 0,
              "notes": ["Focus on depth and control", "Activate glutes"]
            }
          ]
        }
      ]
    },
    {
      "name": "Main Compound Lifts",
      "duration": 30,
      "exercises": [
        {
          "name": "Barbell Back Squats",
          "sets": [
            {
              "reps": "8-10",
              "weight": "heavy (75-80% estimated 1RM)",
              "rest": 120,
              "notes": [
                "Maintain upright torso",
                "Full depth (hip crease below knee)",
                "Drive through heels"
              ]
            },
            {
              "reps": "8-10",
              "weight": "heavy (75-80% estimated 1RM)",
              "rest": 120,
              "notes": ["Focus on controlled eccentric", "Explosive concentric"]
            },
            {
              "reps": "8-10",
              "weight": "heavy (75-80% estimated 1RM)",
              "rest": 120,
              "notes": ["Maintain form - reduce weight if needed"]
            }
          ]
        },
        {
          "name": "Romanian Deadlifts",
          "sets": [
            {
              "reps": "10-12",
              "weight": "moderate (60-70% estimated 1RM)",
              "rest": 90,
              "notes": [
                "Hinge at hips",
                "Feel hamstring stretch",
                "Keep back flat"
              ]
            },
            {
              "reps": "10-12",
              "weight": "moderate",
              "rest": 90,
              "notes": ["Controlled tempo - 3 sec down"]
            },
            {
              "reps": "10-12",
              "weight": "moderate",
              "rest": 90,
              "notes": ["Squeeze glutes at top"]
            }
          ]
        }
      ]
    },
    {
      "name": "Accessory Work",
      "duration": 15,
      "rounds": 3,
      "exercises": [
        {
          "name": "Walking Lunges",
          "sets": [
            {
              "reps": "10 each leg",
              "weight": "bodyweight or light dumbbells",
              "rest": 60,
              "notes": [
                "Step through",
                "Front knee over ankle",
                "Back knee nearly touches floor"
              ]
            }
          ]
        },
        {
          "name": "Plank Hold",
          "sets": [
            {
              "reps": "45-60 seconds",
              "weight": "bodyweight",
              "rest": 60,
              "notes": [
                "Maintain neutral spine",
                "Don't let hips sag",
                "Squeeze glutes and core"
              ]
            }
          ]
        }
      ]
    },
    {
      "name": "Cool Down",
      "duration": 5,
      "exercises": [
        {
          "name": "Static Stretching",
          "sets": [
            {
              "reps": "30 seconds each",
              "weight": "bodyweight",
              "rest": 0,
              "notes": [
                "Quad stretch",
                "Hamstring stretch",
                "Hip flexor stretch",
                "Light foam rolling if available"
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### Strength Workout Guidelines

- **Always use `sections` structure** - never just notes array
- **Specify exercises with detail**: name, sets, reps, weight guidance, rest periods
- **Include warmup and cooldown sections**
- **Weight guidance**: Use relative terms (light/moderate/heavy) or percentages, not absolute weights
- **Reps**: Can be fixed (8), range (8-12), or descriptive (AMRAP, to failure)
- **Rest periods**: In seconds between sets
- **Notes**: Provide form cues, intensity guidance, modifications
- **Section duration**: Estimate in minutes for each block
- **Rounds**: Optional field for circuits (e.g., 3 rounds of exercises)

---

## Type: "other"

Used for sauna, general recovery, travel days, etc. (NOT for strength training)

```json
{
  "type": "other",
  "name": "<descriptive name>",
  "plannedDuration": <minutes as integer>,
  "plannedTSS": {
    "min": <integer>,
    "max": <integer>
  },
  "targetRPE": {
    "min": <1-10>,
    "max": <1-10>
  },
  "notes": [<array of strings>]
}
```

---

## Complete Example Week

```json
{
  "weekNumber": 52,
  "startDate": "2025-11-10",
  "ftp": 300,
  "plannedTSS": {
    "min": 420,
    "max": 460
  },
  "notes": {
    "weekFocus": "Points Race Competition + VO2max Rebuild + Sleep Optimization",
    "specialConsiderations": "Tuesday Rising Empire points race (12 scoring opportunities), sleep recovery protocol post-race, VO2max rebuild to 5x4min @ 350W, single run Sunday"
  },
  "days": [
    {
      "dayNumber": 1,
      "date": "2025-11-10",
      "workouts": [
        {
          "type": "bike",
          "name": "Pre-Race Recovery Spin",
          "plannedDuration": 45,
          "plannedTSS": {
            "min": 25,
            "max": 30
          },
          "targetRPE": {
            "min": 1,
            "max": 2
          },
          "intervals": [
            {
              "name": "Easy Warmup",
              "duration": 600,
              "powerTarget": {
                "type": "range",
                "min": 150,
                "max": 170,
                "unit": "watts"
              },
              "cadenceTarget": {
                "min": 85,
                "max": 95
              }
            },
            {
              "name": "Steady Easy Spin",
              "duration": 1500,
              "powerTarget": {
                "type": "range",
                "min": 175,
                "max": 190,
                "unit": "watts"
              },
              "cadenceTarget": {
                "min": 90,
                "max": 95
              }
            }
          ],
          "notes": [
            "Easy recovery to prep for tomorrow's points race",
            "HR should stay below 135 bpm throughout"
          ]
        }
      ]
    },
    {
      "dayNumber": 2,
      "date": "2025-11-11",
      "workouts": [
        {
          "type": "bike",
          "name": "Zwift Racing League - Points Race",
          "plannedDuration": 90,
          "plannedTSS": {
            "min": 110,
            "max": 130
          },
          "targetRPE": {
            "min": 9,
            "max": 10
          },
          "notes": [
            "POINTS RACE - 12 scoring opportunities",
            "Course: Rising Empire, 42km, 755m elevation",
            "Target climbs for points (your strength at 4.3 w/kg)",
            "Expected NP: 280-300W for full effort"
          ]
        }
      ]
    }
  ]
}
```

---

## Important Reminders

### Duration Units

- **Workout-level `plannedDuration`**: MINUTES (integer)
- **Interval-level `duration`**: SECONDS (integer)
- **Section-level `duration`** (mobility/strength): MINUTES (integer)
- **Exercise set `duration`** (mobility): SECONDS (integer)

### **CRITICAL: Duration Accuracy**

**The sum of all intervals/sections MUST equal the workout's `plannedDuration`.**

This is essential for workout execution - the athlete needs accurate time allocation.

#### For Bike Workouts:

```
plannedDuration (minutes) = SUM of all interval durations (seconds) / 60
```

Example: 45min workout needs intervals totaling 2700 seconds (45 × 60)

#### For Mobility/Strength Workouts:

```
plannedDuration (minutes) = SUM of all exercise durations (accounting for perSide)
```

Example: 45min mobility session needs exercises totaling 45 minutes (2700 seconds)

**CRITICAL CALCULATION RULES:**

- **Warmup**: Typically 5-10 minutes (10-15% of total)
- **Main Work**: 60-70% of total time
- **Cool Down**: 5-10 minutes (10-15% of total)
- **Strength Rest Periods**: Include in total time calculations
  - Example: 3 sets × (30 sec work + 60 sec rest) = 4.5 minutes total
- **Mobility Holds with perSide=true**: Duration is DOUBLED for total time
  - Example: Hip Flexor Stretch with duration=180 and perSide=true = 360 seconds (6 minutes) total
- **Mobility Transitions**: Add 10-15 seconds between exercises
  - Example: 8 exercises × 15 sec transition = 2 minutes additional

**MANDATORY: Before finalizing ANY mobility/strength workout:**

1. Calculate ACTUAL total time of all exercises (accounting for perSide doubling)
2. Add transition time between exercises (10-15 seconds per exercise)
3. Verify total matches `plannedDuration` EXACTLY (±1 minute acceptable)
4. If shortfall exists, ADD MORE EXERCISES or INCREASE durations
5. DO NOT just use the same 7-8 movements - include variety:
   - Core strength exercises (planks, dead bugs, bird dogs)
   - Dynamic movements (lunges, squats, leg swings)
   - Upper body stretches (triceps, shoulders, chest)
   - Additional holds (supine twists, happy baby, seated stretches)

**Example 45-Minute Mobility Workout Calculation:**

```
Warmup (5 min):
- Cat-Cow: 120s = 2 min
- Child's Pose: 180s = 3 min

Main Work (35 min):
- Hip Flexor Stretch: 180s × 2 (perSide) = 6 min
- Hamstring Stretch: 180s × 2 (perSide) = 6 min
- Glute Stretch: 180s × 2 (perSide) = 6 min
- Thoracic Rotation: 120s × 2 (perSide) = 4 min
- Pigeon Pose: 240s × 2 (perSide) = 8 min
- Supine Twist: 120s × 2 (perSide) = 4 min
- Shoulder Opener: 90s × 2 (perSide) = 3 min

Cooldown (5 min):
- Legs Up Wall: 180s = 3 min
- Savasana: 120s = 2 min

Total: 5 + 37 + 5 = 47 minutes ✗ TOO LONG
Adjustment needed: Reduce some durations by 2 minutes total
```

**Common Mistakes to AVOID:**

1. ❌ Using only 7-8 movements from RAG context repeatedly
2. ❌ Forgetting to double durations when perSide=true
3. ❌ Not accounting for transitions between exercises
4. ❌ Generating 15 minutes of content for a 45-minute workout
5. ❌ Repeating the exact same routine every week

**Solution for Variety:**

- Include 12-15 different movements for 45-minute sessions
- Mix static holds, dynamic stretches, and light strengthening
- Rotate through different muscle groups and movement patterns
- Use progressive durations (start shorter, build to longer holds)

### Power Specifications

- When specifying fixed power: use `"min": X, "max": X` (same value)
- For progressive warmups/cooldowns: use percent_ftp with start/end values
- For main intervals: use range in watts for precision

### FTP Field

- **CRITICAL**: The `ftp` field at top level MUST be present and current
- This value is used by the application for:
  - Dynamic Zwift file generation
  - Percent FTP calculations
  - Power zone recommendations
- Update this value whenever Jake's FTP changes (typically after testing)

### Notes Arrays

- Always use array format `["note 1", "note 2"]` even for single items
- Notes provide coaching context but don't affect Zwift file generation
- Keep notes concise but informative

### Validation Checklist

Before providing JSON to Jake:

- [ ] `ftp` field is present at top level
- [ ] All durations use correct units (seconds vs minutes)
- [ ] **Sum of intervals/sections equals `plannedDuration`** ⚠️ CRITICAL
- [ ] All dates use YYYY-MM-DD format
- [ ] Power targets use one of the three valid formats
- [ ] Cadence targets include both min and max
- [ ] All required fields are present for each workout type
- [ ] JSON is valid (no trailing commas, proper brackets)

---

## Version History

- **v1.0** (2025-11-10): Initial template with FTP field requirement added
- **v1.1** (2025-11-17): Added critical duration accuracy requirements and calculation guidelines
