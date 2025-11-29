# AI Coach UI Improvements - November 14, 2025

## Changes Made to Address User Questions

### 1. **Added "How It Works" Instructions**

- Clear 5-step workflow explanation at the top of the AI Coach page
- Helps users understand the entire process before starting
- Explains that they select a COMPLETED week and get a plan for the NEXT week

### 2. **Clarified Date Selection**

- **Old:** "Select Training Week"
- **New:** "Step 1: Select Completed Training Week"
- Added subtitle: "_Choose a week you've already trained - AI will analyze this data and plan your next week_"
- Makes it crystal clear these are PAST dates for analysis

### 3. **Fixed Step Numbering and Descriptions**

- Step 1: Select Completed Training Week
- Step 2: Provide Context (Optional but Recommended)
- Step 3: Generate Weekly Analysis
- Step 4: Generate Next Week's Workout Plan
- Step 5: Save & Export

### 4. **Improved Context Text Areas**

#### Schedule & Constraints:

- **Old:** "📅 Schedule & Constraints"
- **New:** "📅 Upcoming Week Schedule & Constraints"
- Placeholder now emphasizes UPCOMING week events
- Help text clarifies: "Share your schedule for the UPCOMING week"

#### Week Feedback:

- **Old:** "🗣️ Week Feedback & Feelings"
- **New:** "🗣️ Completed Week - Feedback & Feelings"
- Placeholder references completed week activities
- Help text clarifies: "How did you feel during the COMPLETED week you selected above?"

### 5. **Fixed White Text Issue**

- **Old:** Plain white background with default text (could be white on white)
- **New:** Explicit color styling - `color: #333;` for text, `color: #667eea;` for emphasis
- Now readable on all backgrounds

### 6. **Added Descriptive Subtitles**

- Each step now has an italicized explanation of what happens
- Examples:
  - "_AI will analyze your completed week's workout data, performance metrics, and recovery trends_"
  - "_AI will create a personalized 7-day plan for the week following your completed week_"
  - "_Save this plan to your database and automatically generate Zwift workout files_"

## Answers to User's Questions

### Q1: Does the AI coach always just analyze the most recent 7 days?

**A:** No! It analyzes whatever 7-day period you select in the date pickers. It also loads 4 weeks of historical context for comparison trends.

### Q2: What are the dates for - analyzing or proposing?

**A:** Both, but in sequence:

1. You select dates for a **completed** week (e.g., Nov 4-10, 2025)
2. AI **analyzes** those dates (your actual past data)
3. AI **proposes** workouts for the **next** 7 days (Nov 11-17, 2025)

### Q3: White text on white background issue?

**A:** Fixed! Added explicit color styling (`color: #333;`) so the tip text is always readable.

### Q4: Better labels for context boxes?

**A:** Completely redesigned:

- "Upcoming Week Schedule & Constraints" - clearly future-focused
- "Completed Week - Feedback & Feelings" - clearly references the selected past week
- Help text reinforces the timeline distinction

### Q5: What happens when you click "Generate AI Analysis"?

**A:** Here's the exact sequence:

1. Fetches YOUR actual workout data for selected dates from database
2. Gets comprehensive context from previous 4 weeks
3. Loads athlete profile and coaching continuity notes
4. Sends everything to AI with your optional context
5. AI analyzes performance, recovery, trends, patterns
6. Extracts coaching continuity notes (key observations, priorities for next week)
7. Saves continuity to `coaching_notes.json` for future context
8. Displays human-readable analysis as markdown

### Q6: Instructions needed?

**A:** Added! The "How It Works" box at the top explains the entire 5-step workflow before users begin.

## Testing Notes

- All changes are UI-only (no API/backend changes)
- Streamlit app needs to be reloaded to see changes
- Test with a real completed week to verify flow makes sense
- Week 999 (Dec 1-7, 2025) is safe for testing without affecting real data

## Example User Flow

1. **User opens AI Coach tab**

   - Sees "How It Works" explanation
   - Understands they need a completed week

2. **User selects Nov 4-10, 2025 (last week)**

   - Date pickers clearly say "Select Completed Training Week"
   - Subtitle confirms this is for analysis

3. **User adds context:**

   - "Upcoming Week": "Tuesday evening race at 6pm, Thursday travel to Denver"
   - "Completed Week": "Tuesday's threshold felt strong, sleep was great Mon-Wed, legs tired Friday"

4. **User clicks "Generate AI Analysis"**

   - Sees progress spinner
   - AI analyzes Nov 4-10 actual data
   - Gets analysis with insights

5. **User clicks "Generate Workout Plan"**

   - AI creates plan for Nov 11-17 (next week)
   - Sees 7 daily workouts

6. **User clicks "Save Plan"**
   - Plan saved to database
   - Zwift files generated
   - Can now view in Proposed Workouts tab
