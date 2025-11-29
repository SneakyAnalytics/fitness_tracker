# Feature Development Plan - Week of Nov 17, 2025

## Overview

Two major feature improvements to enhance the fitness tracking application:

1. AI-Powered Workout Analysis & Enhanced Dashboard
2. Improved Zwift Text Alerts

---

## Feature 1: AI-Powered Workout Analysis & Enhanced Dashboard

### Goals

- Analyze each workout using Gemini AI as fit files are uploaded
- Track personal best efforts across multiple time intervals
- Create medal system (Gold/Silver/Bronze) for top 3 efforts
- Build interactive time-series graphs for workout visualization
- Enhance weekly AI analysis with individual workout insights

### Components to Build

#### 1.1 Fit File AI Analysis Engine

**File**: `src/utils/fit_file_analyzer.py`

**Capabilities**:

- Parse fit file data (already have `fit_parser.py` - expand it)
- Extract key metrics: power, HR, cadence, speed, elevation
- Detect peak efforts (30s, 1min, 3min, 5min, 10min, 20min power)
- Calculate fastest splits (1mi, 5mi, 10mi, etc.)
- Use Gemini API to generate workout summary/analysis
- Store analysis in database

**Gemini Prompt Template**:

```
Analyze this cycling workout:
- Duration: {duration}
- Average Power: {avg_power}W
- Normalized Power: {np}W
- Peak Efforts: {peaks}
- Heart Rate Data: {hr_data}
- Athlete Notes: {notes}

Provide:
1. Workout quality assessment
2. Effort distribution analysis
3. Notable achievements
4. Recovery recommendations
5. Performance insights
```

#### 1.2 Personal Best Tracking System

**Database Schema** (new table):

```sql
CREATE TABLE personal_bests (
    id INTEGER PRIMARY KEY,
    athlete_id INTEGER,
    effort_type TEXT,  -- '30s_power', '1min_power', '5min_power', '1mi_speed', etc.
    effort_value REAL,  -- watts or mph
    workout_id INTEGER,  -- reference to workout
    achieved_date TEXT,
    rank INTEGER,  -- 1=gold, 2=silver, 3=bronze
    FOREIGN KEY (workout_id) REFERENCES workouts(id)
)
```

**Effort Types to Track**:

- Power: 30s, 1min, 3min, 5min, 10min, 20min, 60min
- Speed: Fastest mile, 5mi, 10mi, 20mi
- Climbing: Highest VAM (vertical meters/hour)
- Heart Rate: Peak 1min, 5min, 10min averages

**Medal Logic**:

- Compare new effort against historical top 3
- If new effort > bronze, update rankings
- Push previous medals down (gold→silver→bronze→off-podium)
- Display in workout summary and dashboard

#### 1.3 Interactive Workout Graphs

**Library**: Plotly (already in requirements.txt)

**Graph Features**:

- Multi-axis time series (power, HR, cadence, speed, elevation)
- Synchronized tooltips on hover
- Zoom/pan capabilities
- Interval markers showing workout structure
- Personal best segments highlighted
- Export to PNG/HTML

**UI Integration** (Streamlit):

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

fig = make_subplots(
    rows=5, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.02,
    subplot_titles=('Power', 'Heart Rate', 'Cadence', 'Speed', 'Elevation')
)

# Add traces for each metric
# Add interval markers
# Add personal best highlights
st.plotly_chart(fig, use_container_width=True)
```

#### 1.4 Enhanced Dashboard

**New Dashboard Tab**: "Performance Analytics"

**Sections**:

1. **Personal Bests Podium**

   - Cards for each effort type
   - Medal icons (🥇🥈🥉)
   - Date achieved, workout name
   - Progress toward next milestone

2. **Peak Power Curve**

   - Plot: Duration (x-axis) vs Power (y-axis)
   - Show current curve vs all-time best
   - Compare against pro cyclist benchmarks

3. **Training Load Trends**

   - TSS by week (bar chart)
   - CTL (chronic training load) line
   - ATL (acute training load) line
   - TSB (training stress balance)

4. **Workout Heatmap**

   - Calendar view with TSS intensity colors
   - Hover shows workout details
   - Click to drill into specific workout

5. **Zone Distribution**
   - Pie chart: time in each power zone
   - Compare actual vs planned distribution
   - Weekly/monthly/yearly views

#### 1.5 Integration with Weekly AI Analysis

**Enhancement**: Include individual workout AI summaries in weekly prompt

**Current Prompt Addition**:

```
INDIVIDUAL WORKOUT INSIGHTS:
Monday - Recovery Spin:
{gemini_analysis_from_fit_file}
Key Metrics: {metrics}
Personal Bests: {any_pbs_achieved}

Tuesday - VO2max Intervals:
{gemini_analysis_from_fit_file}
...
```

This gives the weekly AI more context for recommendations.

---

## Feature 2: Improved Zwift Text Alerts

### Current Issues

1. ✅ **Too many quotes** - Need more variety (jokes, facts, workout cues)
2. ✅ **Repetition** - Same messages appearing multiple times per workout
3. ✅ **Too brief** - Messages disappear too quickly
4. ✅ **Not contextual** - Messages don't match interval type

### Solutions

#### 2.1 Expand Content Library

**File**: `src/utils/dynamic_workout_content.py`

**Current Categories** (expand each to 50+ messages):

- Welcome messages (5 → 20)
- Recovery messages (7 → 50)
- Intensity messages (8 → 50)
- Encouragement (7 → 50)
- Humor/Jokes (7 → 100)
- Science facts (7 → 100)
- Closing messages (7 → 20)

**New Categories**:

- **Interval-Specific Cues**: Messages tied to interval name
  - "VO2max" → "Push through the burn! Your VO2max is increasing!"
  - "Threshold" → "This is where you build FTP! Hold steady!"
  - "Sprint" → "Unleash maximum power NOW!"
- **Workout Phase Messages**:

  - Warmup: "Ease into it, prime the engine"
  - Main set: "This is what you came for!"
  - Cooldown: "Recovery mode activated"

- **Motivational Quotes** (keep but limit to 10% of messages):

  - Current overuse: 90% quotes → Target: 10% quotes

- **Cycling History/Trivia**:
  - "Eddy Merckx won 525 races in his career!"
  - "The hour record is 56.792 km - set by Filippo Ganna"
  - "Tour de France riders burn 8,000+ calories per day!"

#### 2.2 Smart Message Selection Algorithm

**Current Issue**: Messages repeat because `used_messages` isn't working properly

**Fix**:

```python
def get_fresh_content(self, category: str, context: dict = None) -> str:
    """Get non-repeating content based on category and context"""

    # Get available messages for this category
    available = [msg for msg in self.content[category]
                 if msg not in self.used_messages]

    # If all messages used, reset pool
    if not available:
        self.used_messages.clear()
        available = self.content[category]

    # Weight by context (e.g., prefer science facts during recovery)
    if context:
        weighted_selection = self._apply_context_weighting(available, context)
        message = random.choice(weighted_selection)
    else:
        message = random.choice(available)

    self.used_messages.add(message)
    return message
```

#### 2.3 Increase Message Frequency & Duration

**Current**: ~3-5 messages per workout at random times

**Target**: 1 message every 2-3 minutes

**Placement Strategy**:

- Workout start (welcome)
- Start of each interval (context-specific cue)
- Midpoint of long intervals (encouragement)
- End of hard intervals (celebration)
- Recovery intervals (science/humor)
- Workout end (closing/stats)

**XML Changes**:

```xml
<!-- Current -->
<textevent timeoffset="10" message="Keep pushing!"/>

<!-- New: Longer duration attribute if possible -->
<textevent timeoffset="10" duration="10" message="Keep pushing! You're building FTP!"/>
```

**Note**: Zwift may not support duration attribute - if not, use longer messages that naturally take longer to read.

#### 2.4 Context-Aware Message Selection

**Match message type to interval characteristics**:

```python
def select_message_for_interval(interval: dict) -> str:
    """Pick message based on interval type"""

    power_pct = interval.get_power_percent()
    duration = interval.get('duration', 0)
    name = interval.get('name', '').lower()

    # Recovery intervals (< 60% FTP)
    if power_pct < 0.60:
        categories = ['recovery', 'science', 'humor']
        weights = [0.5, 0.3, 0.2]

    # Threshold intervals (75-95% FTP)
    elif 0.75 <= power_pct < 0.95:
        categories = ['intensity', 'encouragement', 'science']
        weights = [0.5, 0.3, 0.2]

    # VO2max intervals (> 95% FTP)
    elif power_pct >= 0.95:
        categories = ['intensity', 'encouragement']
        weights = [0.7, 0.3]

    # Long endurance (> 20min at moderate)
    elif duration > 1200:
        categories = ['encouragement', 'science', 'humor']
        weights = [0.4, 0.4, 0.2]

    return weighted_random_choice(categories, weights)
```

---

## Implementation Timeline

### Week Plan (Nov 17-23, 2025)

**Monday (Nov 18)**:

- ✅ Fix Zwift text alert repetition bug
- ✅ Expand content library (add 200+ new messages)
- ✅ Implement context-aware message selection
- ✅ Test with existing Week 53 workouts

**Tuesday (Nov 19)**:

- Build personal best detection in fit_parser.py
- Create personal_bests database table
- Implement ranking/medal logic
- Test with historical fit files

**Wednesday (Nov 20)**:

- Build Gemini integration for fit file analysis
- Create workout analysis prompt template
- Store analyses in database
- Test with sample workouts

**Thursday (Nov 21)**:

- Build Plotly interactive graphs
- Add to workout detail view
- Implement multi-axis time series
- Add interval markers and PB highlights

**Friday (Nov 22)**:

- Create Performance Analytics dashboard tab
- Build personal bests podium display
- Add peak power curve graph
- Implement training load trends

**Saturday (Nov 23)**:

- Integration: Connect workout AI analysis to weekly AI prompt
- Testing: End-to-end workflow
- Polish UI/UX
- Documentation

**Sunday (Nov 24)**:

- Buffer day for bug fixes
- User testing with real workouts
- Performance optimization

---

## Success Metrics

### Feature 1: AI Analysis & Dashboard

- ✅ Gemini successfully analyzes 100% of uploaded fit files
- ✅ Personal bests detected automatically within 1 minute of upload
- ✅ Interactive graphs load in < 2 seconds
- ✅ Dashboard provides actionable insights
- ✅ Weekly AI analysis includes individual workout context

### Feature 2: Text Alerts

- ✅ Zero repeated messages within same workout
- ✅ < 10% of messages are quotes
- ✅ Messages appear every 2-3 minutes during workout
- ✅ Messages are contextually appropriate to interval type
- ✅ Mix of motivation, humor, science, and cues

---

## Technical Considerations

### Gemini API

- Already integrated ✅
- Free tier: 10 requests/min
- Cost per fit file analysis: ~$0.001 (negligible)
- Latency: ~2-5 seconds per analysis

### Database Performance

- Add indexes on personal_bests.effort_type and athlete_id
- Archive old workout data (> 2 years) to separate table
- Use SQLite FTS for searchable workout notes

### Plotly Performance

- Downsample data for long workouts (> 5 hours)
- Lazy load graphs (only render when tab opened)
- Cache rendered plots in session state

### Message Content Management

- Store messages in JSON file for easy editing
- Allow custom messages via config
- Community contribution system for new content?

---

## Open Questions

1. **Personal Best Categories**: Should we track running/swimming PBs too, or cycling only?
2. **Graph Export**: Want ability to share graphs on social media?
3. **AI Analysis Storage**: Keep all historical analyses or just last 90 days?
4. **Text Alert Customization**: Want ability to disable certain message types?
5. **Dashboard Widgets**: Which metrics are most important to you day-to-day?

---

## Next Steps

Ready to start! Which feature would you like to tackle first:

- **Option A**: Fix text alerts (quick win, improves immediate experience)
- **Option B**: Build AI analysis system (bigger impact, takes longer)
- **Option C**: Start with dashboard graphs (visual appeal, good foundation)

Let me know your preference and we'll dive in! 🚀
