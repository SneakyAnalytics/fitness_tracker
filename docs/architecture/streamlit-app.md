# Streamlit App Architecture

## Overview

The Streamlit UI is the primary interface for the fitness tracker application. It's a single 4,400+ line file (`src/ui/streamlit_app.py`) that provides:

- Password-protected access
- Multiple tabs for different features
- Real-time data visualization
- Interactive workout tracking
- AI coaching interface

**File:** [src/ui/streamlit_app.py](../../src/ui/streamlit_app.py)  
**Lines:** 4,427 lines  
**Tech Stack:** Streamlit, Plotly, Pandas, Requests (to FastAPI backend)

## Application Flow

```
User Opens Browser
    ↓
Password Protection (check_password)
    ↓
Load CSS Styling (apply_custom_styling)
    ↓
Initialize Session State
    ↓
Render Tab Navigation
    ├── 📊 Dashboard (default)
    ├── 📅 Calendar
    ├── 🤖 AI Coach
    ├── 💪 Workout Tracking
    ├── 📈 Analytics
    ├── 🔄 Session Comparison
    ├── ⚙️ Settings
    └── 📝 Recovery Notes
```

## Main Components

### 1. Authentication (Lines 11-50)

**Function:** `check_password()`

```python
def check_password():
    """Returns True if user has entered the correct password."""
    correct_password = os.getenv("STREAMLIT_PASSWORD", "fitness2026")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # Show login form
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if password == correct_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Incorrect password")

    return False

# Check password before loading the rest of the app
if not check_password():
    st.stop()
```

**Features:**

- Session-based authentication
- Environment variable password (`STREAMLIT_PASSWORD`)
- Default password: "fitness2026"
- Stops app execution if not authenticated

### 2. Custom Styling (Lines 122-327)

**Function:** `apply_custom_styling()`

Applies custom CSS for:

- Gradient header backgrounds
- Metric card styling
- Sidebar color schemes
- Button hover effects
- Form input styling
- Responsive design

**Usage:**

```python
apply_custom_styling()
st.markdown('<div class="main-header"><h1>🏃 Fitness Tracker</h1></div>', unsafe_allow_html=True)
```

### 3. Helper Functions (Lines 328-362)

**`create_custom_metric(title, value, icon, color)`**

```python
def create_custom_metric(title, value, icon="📊", color="blue"):
    """Create a styled metric card"""
    return f"""
    <div class="metric-card {color}">
        <div class="metric-icon">{icon}</div>
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """
```

**`create_section_header(text, icon)`**

```python
def create_section_header(text, icon="🏃‍♂️"):
    """Create a styled section header"""
    return f"<h2 style='color: #56ab2f;'>{icon} {text}</h2>"
```

**`create_workout_badge(workout_type)`**

```python
def create_workout_badge(workout_type):
    """Create a colored badge for workout types"""
    colors = {
        "Bike": "#56ab2f",
        "Run": "#ff6b6b",
        "Swim": "#4dabf7",
        "Strength": "#ff922b"
    }
    return f"<span style='background: {colors.get(workout_type, '#868e96')};'>...</span>"
```

## Tab Structure

### Tab 1: 📊 Dashboard (Lines 363-637)

**Function:** `display_weekly_summary(summary)`

**Features:**

- Weekly training metrics (TSS, hours, sessions)
- Workout type distribution pie chart
- Daily training load bar chart
- Recent workouts list with badges
- AI-generated weekly summary

**Key Visualizations:**

```python
# Workout distribution pie chart
fig = px.pie(
    values=list(workout_type_counts.values()),
    names=list(workout_type_counts.keys()),
    title="Workout Distribution"
)

# Daily TSS bar chart
fig = px.bar(
    x=dates,
    y=tss_values,
    title="Daily Training Load"
)
```

**API Calls:**

```python
response = requests.get(f"{API_URL}/summary", params={
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat()
})
```

### Tab 2: 📅 Calendar (Lines 1105-1475)

**Function:** `display_workout_calendar()`

**Features:**

- Month/year selector
- Calendar grid with workout dots
- Color-coded by workout type
- Click to view workout details
- Shows completed vs planned workouts

**Rendering Logic:**

```python
# Create calendar grid (7 columns for days of week)
cols = st.columns(7)
for day_num in range(1, days_in_month + 1):
    col_index = (start_day + day_num - 1) % 7
    with cols[col_index]:
        # Show workout indicators for this day
        day_workouts = [w for w in workouts if w['workout_day'] == f"{year}-{month:02d}-{day_num:02d}"]
        if day_workouts:
            st.button(f"🟢 {day_num}", key=f"day_{day_num}")
        else:
            st.button(f"⚪ {day_num}", key=f"day_{day_num}")
```

### Tab 3: 🤖 AI Coach (Lines 2283-2897)

**Function:** `display_ai_coach()`

**Most Complex Tab - Multi-Step Workflow:**

**Step 1: Select Week Number**

```python
week_number = st.number_input("Week Number", min_value=1, max_value=52)
start_date = st.date_input("Week Start Date (Monday)")
```

**Step 2: Set Training Targets**

```python
tss_range = st.slider("Planned TSS Range", min_value=0, max_value=1000, value=(300, 400))
```

**Step 3: Generate Weekly Plan**

```python
if st.button("Generate Weekly Plan"):
    response = requests.post(f"{API_URL}/ai-coach/generate-weekly-plan", json={
        "week_number": week_number,
        "start_date": start_date.isoformat(),
        "planned_tss_min": tss_range[0],
        "planned_tss_max": tss_range[1],
        "notes": notes
    })
```

**Step 4: Review and Edit Daily Plans**

```python
for day_number in range(1, 8):
    with st.expander(f"Day {day_number} - {day_date}"):
        # Show proposed workouts for this day
        for workout in day_workouts:
            st.write(f"**{workout['name']}**")
            st.write(f"Type: {workout['type']}")
            st.write(f"Duration: {workout['plannedDuration']} min")
            st.write(f"TSS: {workout['plannedTSS_min']}-{workout['plannedTSS_max']}")

            # Show intervals if available
            if workout['intervals']:
                intervals = json.loads(workout['intervals'])
                for interval in intervals:
                    st.write(f"- {interval['type']}: {interval['duration']}s @ {interval['power']} FTP")
```

**Step 5: Generate Zwift .zwo Files**

```python
if st.button("Generate Zwift Workout Files"):
    response = requests.post(f"{API_URL}/ai-coach/generate-zwift-files", json={
        "week_number": week_number
    })
    st.success(f"Generated {len(files)} .zwo files")
```

**Data Flow in AI Coach Tab:**

```
User Input (week, dates, TSS targets)
    ↓
POST /ai-coach/generate-weekly-plan
    ↓
Claude/Gemini generates plan
    ↓
Plan stored in DB (weekly_plans, daily_plans, proposed_workouts)
    ↓
Display in UI with edit capabilities
    ↓
User confirms or edits
    ↓
POST /ai-coach/generate-zwift-files
    ↓
Generate .zwo files from proposed_workouts
    ↓
Files saved to ZWIFT_WORKOUTS_DIR
```

### Tab 4: 💪 Workout Tracking (Lines 1476-2091)

**Three Workout Type Handlers:**

**4a. Bike Workouts**
**Function:** `display_bike_workout(workout)`

```python
def display_bike_workout(workout):
    """Display and track bike workout details"""

    # Show workout overview
    st.write(f"**{workout['name']}**")
    st.write(f"Duration: {workout['plannedDuration']} min")
    st.write(f"Target TSS: {workout['plannedTSS_min']}-{workout['plannedTSS_max']}")

    # Show interval structure
    intervals = json.loads(workout['intervals'])
    for interval in intervals:
        st.write(f"- {interval['type']}: {interval['duration']}s")
        st.write(f"  Power: {interval['power']['min']*100:.0f}%-{interval['power']['max']*100:.0f}% FTP")

    # Performance tracking
    completed = st.checkbox("Mark as Completed")
    if completed:
        actual_duration = st.number_input("Actual Duration (min)")
        average_power = st.number_input("Average Power (watts)")
        normalized_power = st.number_input("Normalized Power (watts)")

        if st.button("Save Performance"):
            # Save to database
            pass
```

**4b. Run Workouts**
**Function:** `display_run_workout(workout)`

```python
def display_run_workout(workout):
    """Display run workout with pace/HR zones"""

    # Show run-specific metrics
    st.write(f"Target Pace: {workout['targetPace']}")
    st.write(f"Distance: {workout['distance']} km")

    # HR zone targeting
    if 'hrZones' in workout:
        st.write("Heart Rate Zones:")
        for zone in workout['hrZones']:
            st.write(f"- Zone {zone['zone']}: {zone['min']}-{zone['max']} bpm")
```

**4c. Strength Workouts**
**Function:** `display_strength_workout_with_tracking(workout, unique_key)`

```python
def display_strength_workout_with_tracking(workout, unique_key=""):
    """Display strength workout with set tracking"""

    # Show exercise list
    exercises = json.loads(workout['sections'])
    for exercise in exercises:
        st.write(f"**{exercise['name']}**")
        st.write(f"Sets: {exercise['sets']} x {exercise['reps']} reps")
        st.write(f"Weight: {exercise['weight']} lbs")

        # Track each set
        for set_num in range(exercise['sets']):
            col1, col2, col3 = st.columns(3)
            with col1:
                actual_reps = st.number_input(f"Set {set_num+1} Reps", key=f"{unique_key}_set{set_num}_reps")
            with col2:
                actual_weight = st.number_input(f"Set {set_num+1} Weight", key=f"{unique_key}_set{set_num}_weight")
            with col3:
                completed = st.checkbox(f"✓", key=f"{unique_key}_set{set_num}_done")
```

**4d. Workout Timer**
**Function:** `create_workout_timer()`

```python
def create_workout_timer():
    """Interactive countdown timer for workouts"""

    if 'timer_running' not in st.session_state:
        st.session_state.timer_running = False
        st.session_state.timer_seconds = 0

    # Timer controls
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ Start"):
            st.session_state.timer_running = True
    with col2:
        if st.button("⏸️ Pause"):
            st.session_state.timer_running = False
    with col3:
        if st.button("🔄 Reset"):
            st.session_state.timer_seconds = 0

    # Display timer
    minutes = st.session_state.timer_seconds // 60
    seconds = st.session_state.timer_seconds % 60
    st.markdown(f"<h1 style='text-align: center;'>{minutes:02d}:{seconds:02d}</h1>", unsafe_allow_html=True)

    # Auto-increment timer
    if st.session_state.timer_running:
        time.sleep(1)
        st.session_state.timer_seconds += 1
        st.rerun()
```

### Tab 5: 📈 Analytics (Lines 638-1104)

**Function:** `display_performance_analytics()`

**Features:**

- Personal bests tracking (5s, 1min, 5min, 20min, 60min power)
- Power curve visualization
- Historical performance trends
- Training load progression
- Heart rate zone analysis

**Key Visualizations:**

**Power Curve:**

```python
# Get power curve data from multiple FIT files
durations = [5, 30, 60, 300, 1200, 3600]
best_powers = []

for duration in durations:
    best_power = max([
        get_best_power(fit_file, duration)
        for fit_file in fit_files
    ])
    best_powers.append(best_power)

# Plot power curve
fig = px.line(
    x=durations,
    y=best_powers,
    title="Power Curve",
    labels={"x": "Duration (seconds)", "y": "Power (watts)"}
)
st.plotly_chart(fig)
```

**Training Load Progression:**

```python
# Get weekly TSS over time
weeks = []
weekly_tss = []

for week_start in date_range:
    week_data = get_week_summary(week_start)
    weeks.append(week_start)
    weekly_tss.append(week_data['total_tss'])

# Plot TSS progression
fig = px.bar(
    x=weeks,
    y=weekly_tss,
    title="Weekly Training Load",
    labels={"x": "Week", "y": "TSS"}
)
st.plotly_chart(fig)
```

**Personal Bests Table:**

```python
# Get personal bests from database
personal_bests = get_personal_bests()

# Display as table
pb_data = {
    "Duration": ["5 seconds", "1 minute", "5 minutes", "20 minutes", "60 minutes"],
    "Power (W)": [pb['5s'], pb['1min'], pb['5min'], pb['20min'], pb['60min']],
    "W/kg": [pb['5s']/weight, pb['1min']/weight, pb['5min']/weight, pb['20min']/weight, pb['60min']/weight],
    "Date": [pb['5s_date'], pb['1min_date'], pb['5min_date'], pb['20min_date'], pb['60min_date']]
}

st.dataframe(pd.DataFrame(pb_data))
```

### Tab 6: 🔄 Session Comparison (Lines 2898-3054)

**Function:** `display_session_comparison_page()`

**Features:**

- Compare two workouts side-by-side
- Power/HR/Cadence overlay charts
- Interval-by-interval comparison
- Performance delta analysis

**Comparison Visualization:**

```python
def display_session_comparison_page():
    st.header("🔄 Session Comparison")

    # Select two workouts
    col1, col2 = st.columns(2)
    with col1:
        workout1 = st.selectbox("Workout 1", workout_list)
    with col2:
        workout2 = st.selectbox("Workout 2", workout_list)

    if workout1 and workout2:
        # Get FIT file data
        fit1 = get_fit_file(workout1['fit_file_id'])
        fit2 = get_fit_file(workout2['fit_file_id'])

        # Overlay power curves
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=fit1['time'],
            y=fit1['power'],
            name=workout1['workout_title'],
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=fit2['time'],
            y=fit2['power'],
            name=workout2['workout_title'],
            line=dict(color='red')
        ))
        st.plotly_chart(fig)

        # Compare metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg Power",
                     f"{fit1['avg_power']} W",
                     delta=f"{fit1['avg_power'] - fit2['avg_power']} W")
        with col2:
            st.metric("Normalized Power",
                     f"{fit1['np']} W",
                     delta=f"{fit1['np'] - fit2['np']} W")
        with col3:
            st.metric("TSS",
                     f"{fit1['tss']}",
                     delta=f"{fit1['tss'] - fit2['tss']}")
```

### Tab 7: 📝 Recovery Notes (Lines 3055-4300)

**Function:** Part of main app flow (no single function)

**Features:**

- Daily energy level tracking (1-10 scale)
- Sleep quality assessment
- Muscle soreness mapping (body diagram)
- General fatigue tracking
- Workout-specific feedback forms

**Recovery Data Structure:**

```python
recovery_data = {
    'daily_energy': {
        '2026-01-12': 7,
        '2026-01-13': 8,
        '2026-01-14': 6,
        # ... for each day of week
    },
    'daily_sleep_quality': {
        '2026-01-12': 8,
        '2026-01-13': 7,
        # ...
    },
    'muscle_soreness_patterns': {
        'legs': {'severity': 6, 'notes': 'Quads tight after intervals'},
        'back': {'severity': 2, 'notes': 'Minor tightness'}
    },
    'general_fatigue_level': 5,
    'qualitative_feedback': [
        {
            'workout_title': 'Threshold Development 2x15min',
            'date': '2026-01-15',
            'type': 'bike',
            'feedback': {
                'difficulty': 'hard',
                'notes': 'Second interval was tough, held power well'
            }
        }
    ]
}
```

**Save Recovery Notes:**

```python
if st.button("Save Recovery Notes"):
    response = requests.post(f"{API_URL}/summary/save", json={
        'start_date': week_start.isoformat(),
        'end_date': week_end.isoformat(),
        'total_tss': calculated_tss,
        'total_training_hours': calculated_hours,
        'sessions_completed': num_sessions,
        'daily_energy': daily_energy_dict,
        'daily_sleep_quality': daily_sleep_dict,
        'muscle_soreness_patterns': soreness_dict,
        'general_fatigue_level': fatigue_level,
        'qualitative_feedback': feedback_list,
        'workout_types': ['bike', 'strength', 'mobility']
    })

    if response.status_code == 200:
        st.success("Recovery notes saved!")
```

## Session State Management

Streamlit uses `st.session_state` for state persistence across reruns:

```python
# Initialize session state variables
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'selected_workout_id' not in st.session_state:
    st.session_state.selected_workout_id = None

if 'timer_running' not in st.session_state:
    st.session_state.timer_running = False
    st.session_state.timer_seconds = 0

if 'current_week_plan' not in st.session_state:
    st.session_state.current_week_plan = None

if 'notes_saved' not in st.session_state:
    st.session_state.notes_saved = False
```

**Session State Best Practices:**

```python
# ✅ DO: Check before accessing
if 'key' in st.session_state:
    value = st.session_state.key

# ✅ DO: Use for form state
st.session_state.form_data = {'name': 'workout', 'duration': 60}

# ❌ DON'T: Store large objects (causes memory issues)
# st.session_state.all_workouts = [thousands of workout objects]

# ❌ DON'T: Store database connections
# st.session_state.db_conn = sqlite3.connect(...)
```

## API Communication

All backend communication happens through the FastAPI backend:

```python
API_URL = os.getenv("API_URL", "http://localhost:8000")

# GET request
response = requests.get(f"{API_URL}/workouts", params={
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat()
})
workouts = response.json()

# POST request
response = requests.post(f"{API_URL}/ai-coach/generate-weekly-plan", json={
    "week_number": 61,
    "start_date": "2026-01-12",
    "planned_tss_min": 300,
    "planned_tss_max": 400
})
plan = response.json()

# Error handling
try:
    response = requests.get(f"{API_URL}/workouts/{workout_id}")
    response.raise_for_status()  # Raises HTTPError for 4xx/5xx
    workout = response.json()
except requests.exceptions.HTTPError as e:
    st.error(f"API Error: {e}")
except requests.exceptions.ConnectionError:
    st.error("Cannot connect to API. Is the backend running?")
```

## Common Patterns

### Date Normalization

```python
def _normalize_date_widget(d: Any) -> Optional[date]:
    """Normalize date input from various sources"""
    if d is None:
        return None
    if isinstance(d, date):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        return datetime.fromisoformat(d).date()
    return None
```

### Form Reset

```python
def reset_form_state():
    """Reset form state after submission"""
    keys_to_delete = [k for k in st.session_state.keys() if k.startswith('form_')]
    for key in keys_to_delete:
        del st.session_state[key]
```

### Metric Display

```python
# Display metrics in columns
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total TSS", f"{total_tss:.0f}")
with col2:
    st.metric("Training Hours", f"{total_hours:.1f}")
with col3:
    st.metric("Sessions", sessions_completed)
with col4:
    st.metric("Avg TSS/Session", f"{avg_tss:.0f}")
```

## Performance Considerations

### 1. Caching API Calls

```python
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_workouts_cached(start_date, end_date):
    response = requests.get(f"{API_URL}/workouts", params={
        "start_date": start_date,
        "end_date": end_date
    })
    return response.json()
```

### 2. Lazy Loading

```python
# Don't load all FIT files at once
if st.button("Show FIT File Details"):
    fit_data = get_fit_file(workout['fit_file_id'])
    display_fit_file_analysis(fit_data)
```

### 3. Pagination

```python
# Paginate large workout lists
workouts_per_page = 10
page = st.number_input("Page", min_value=1, value=1)
start_idx = (page - 1) * workouts_per_page
end_idx = start_idx + workouts_per_page
display_workouts = all_workouts[start_idx:end_idx]
```

## Testing the UI

### Local Testing

```bash
cd /Users/jacobrobinson/fitness_tracker

# Start backend first
docker compose up -d fitness-tracker-api

# Run Streamlit locally
streamlit run src/ui/streamlit_app.py

# Or via Docker
docker compose up -d
open http://localhost:8501
```

### Testing Checklist

- [ ] Login works with correct/incorrect password
- [ ] All tabs load without errors
- [ ] API calls return data successfully
- [ ] Forms submit and save correctly
- [ ] Charts render with data
- [ ] Date pickers work across browsers
- [ ] Session state persists across page interactions
- [ ] Responsive layout on mobile devices

## Deployment

### Environment Variables

```bash
STREAMLIT_PASSWORD=your_secure_password
API_URL=http://fitness-tracker-api:8000  # Docker internal
# API_URL=http://localhost:8000  # Local development
```

### Docker Configuration

```yaml
# docker-compose.yml
services:
  fitness-tracker-ui:
    build: .
    command: streamlit run src/ui/streamlit_app.py
    ports:
      - "8501:8501"
    environment:
      - STREAMLIT_PASSWORD=${STREAMLIT_PASSWORD}
      - API_URL=http://fitness-tracker-api:8000
    depends_on:
      - fitness-tracker-api
```

### Health Check

```python
# Check if app is running
curl http://localhost:8501/_stcore/health
```

## Common Issues

### 1. "This app has encountered an error"

- **Cause**: Uncaught exception in Streamlit code
- **Fix**: Check Docker logs: `docker logs fitness-tracker-ui`
- **Prevention**: Add try-except blocks around API calls

### 2. Infinite Rerun Loop

- **Cause**: State change triggering rerun inside conditional
- **Fix**: Use `st.rerun()` only when necessary
- **Prevention**: Check session state before modifying

### 3. Charts Not Displaying

- **Cause**: Empty data or incompatible data format
- **Fix**: Validate data before passing to Plotly
- **Prevention**: Add data checks before visualization

### 4. API Connection Refused

- **Cause**: Backend not running or wrong URL
- **Fix**: Check `API_URL` environment variable
- **Prevention**: Add connection error handling

## Next Steps

- **Backend API**: [api-endpoints.md](./api-endpoints.md) - See what endpoints the UI calls
- **Database**: [database-schema.md](./database-schema.md) - Understand the data structure
- **Development**: [../agent-instructions/getting-started.md](../agent-instructions/getting-started.md) - Start contributing
