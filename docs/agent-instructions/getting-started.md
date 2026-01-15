# Getting Started Guide for AI Agents

## Prerequisites Knowledge

Before working on this codebase, you should understand:

- Python 3.12+ (async/await, type hints, dataclasses)
- FastAPI framework basics
- Streamlit framework basics
- SQLite and SQL queries
- Docker and Docker Compose
- Basic TrainingPeaks API concepts
- FIT file format basics (for cycling data)

## First-Time Setup

### 1. Clone and Navigate

```bash
cd /Users/jacobrobinson/fitness_tracker
```

### 2. Understand the Environment Variables

Located in `.env` file:

```bash
# AI API Keys
ANTHROPIC_API_KEY=...          # Claude for AI coaching
GOOGLE_API_KEY=...             # Gemini as backup

# TrainingPeaks Credentials
TP_USERNAME=...                # For workout sync
TP_PASSWORD=...

# Paths
ZWIFT_WORKOUTS_DIR=/Users/jacobrobinson/Documents/Zwift/Workouts/6870291
FIT_FILES_DIR=...
```

**IMPORTANT**: Never commit `.env` file. Use `.env.example` as template.

### 3. Check the Database

```bash
sqlite3 data/fitness_data.db
# Run: .tables to see all tables
# Run: .schema workouts to see structure
```

### 4. Start the Application

```bash
# Start containers
docker compose up -d

# View logs
docker logs -f fitness-tracker-ui
docker logs -f fitness-tracker-api

# Access UI
open http://localhost:8501
```

## Understanding the Data Flow

### Workout Sync Flow

```
TrainingPeaks (Web)
  → Playwright automation downloads CSV + FIT files
  → CSV parsed into `workouts` table
  → FIT file parsed into `fit_files` table
  → Matching algorithm links workout_id ↔ fit_file_id
  → Interval detection analyzes power data
  → Results stored in `workout_analyses` table
  → AI generates weekly summary from analyses
```

### AI Coaching Flow

```
User requests weekly plan
  → System queries `workouts` + `workout_analyses` for past week
  → AI Coach Engine builds comprehensive prompt
  → Claude/Gemini generates training plan
  → Plan parsed into structured JSON
  → Stored in `weekly_plans`, `daily_plans`, `proposed_workouts` tables
  → For bike workouts: .zwo files generated for Zwift
  → User views plan in Streamlit UI
```

### Key Data Relationships

```
workouts (1) ←→ (1) fit_files  [via fit_file_id]
workouts (1) ←→ (0..1) workout_analyses [via workout_id]
weekly_plans (1) ←→ (7) daily_plans [via weekNumber]
daily_plans (1) ←→ (1..n) proposed_workouts [via dailyPlanId]
```

## Common Code Patterns

### Database Access

```python
from src.storage.database import WorkoutDatabase

db = WorkoutDatabase()
# Database uses context managers internally
# Don't try to access db.conn directly
```

### Async Functions (FastAPI)

```python
@app.get("/api/workouts")
async def get_workouts():
    # Use async for I/O operations
    result = await some_async_function()
    return result
```

### Error Handling

```python
try:
    result = risky_operation()
except SpecificException as e:
    print(f"⚠️ Warning: {e}")
    # Handle gracefully, don't crash
except Exception as e:
    print(f"❌ Error: {e}")
    # Log and return error response
```

### Interval Detection Pattern

```python
from src.utils.interval_detector import IntervalDetector
from src.utils.interval_classifier import IntervalClassifier

# Always use athlete's FTP from database
detector = IntervalDetector(ftp=athlete_ftp)
intervals = detector.detect_intervals(power_stream, hr_stream, cadence_stream)

classifier = IntervalClassifier(ftp=athlete_ftp)
classified = classifier.classify_intervals(intervals)
```

## File Organization

### Core Application (`src/`)

- **api/app.py**: FastAPI endpoints
- **ui/streamlit_app.py**: Main Streamlit UI (3900+ lines)
- **storage/database.py**: All database operations (2800+ lines)
- **utils/**: Reusable modules (parsers, AI, analysis, etc.)

### Configuration Files

- **docker-compose.yml**: Container definitions
- **Dockerfile**: Container image build
- **requirements.txt**: Python dependencies
- **pytest.ini**: Test configuration

### Data Files

- **data/fitness_data.db**: SQLite database (main data store)
- **data/ai_coach_output/**: Generated AI plans (JSON)
- **logs/**: Application logs

### Scripts

- **Root .py files**: One-off utilities (analysis, fixes, migrations)
- **scripts/**: Reusable utility scripts
- **bin/**: Start/stop scripts

## Testing Before Changes

### 1. Always Test Locally First

```bash
# Stop existing containers
docker compose down

# Start fresh
docker compose up -d

# Wait for healthy status
docker ps

# Test key functionality:
# - Visit http://localhost:8501
# - Try syncing workouts (if safe)
# - Generate a weekly plan (use test data if possible)
# - Check database integrity
```

### 2. Check for Import Errors

```bash
# Test imports
docker exec fitness-tracker-api python -c "from src.storage.database import WorkoutDatabase; print('OK')"
```

### 3. Verify Database Queries

```bash
# Check if your changes broke any queries
docker exec fitness-tracker-api python -c "
from src.storage.database import WorkoutDatabase
db = WorkoutDatabase()
# Test a query that uses your changes
"
```

## Deploying to Beelink

### Via Sync Script (Recommended)

```bash
# Sync entire directory
cd /Users/jacobrobinson/fitness_tracker
./sync_to_beelink.sh 100.117.194.8

# SSH in and restart
ssh rakej@100.117.194.8 "cd C:\Users\rakej\fitness_tracker && docker compose restart"
```

### Manual Deployment

```bash
# Copy specific files
scp changed_file.py rakej@100.117.194.8:C:/Users/rakej/fitness_tracker/

# Restart specific container
ssh rakej@100.117.194.8 "docker restart fitness-tracker-ui"
```

### Verify Deployment

```bash
# Check container status
ssh rakej@100.117.194.8 "docker ps"

# Check logs for errors
ssh rakej@100.117.194.8 "docker logs --tail 50 fitness-tracker-ui"

# Test the UI
curl http://100.117.194.8:8501
```

## Common Gotchas

### Path Differences (Mac vs Windows)

```python
# ❌ DON'T hardcode paths
path = "/Users/jacobrobinson/Documents/Zwift"

# ✅ DO use environment variables
path = os.getenv('ZWIFT_WORKOUTS_DIR', '~/Documents/Zwift')
path = os.path.expanduser(path)  # Expand ~ properly
```

### Database Column Names

```python
# ❌ OLD column names (will break queries)
workout_date, workout_name, workout_type

# ✅ CORRECT column names
workout_day, workout_title, json_extract(workout_data, '$.type')
```

### Interval Detection Requires FTP

```python
# ❌ DON'T use hardcoded FTP
detector = IntervalDetector(ftp=300)

# ✅ DO get FTP from athlete settings
ftp = db.get_athlete_setting('ftp') or 300
detector = IntervalDetector(ftp=ftp)
```

### AI Analysis Data Format

```python
# Handle both string and dict formats
analysis_data = analysis.get('analysis_data', {})
if isinstance(analysis_data, str):
    analysis_data = json.loads(analysis_data)

# Handle both old and new peak_efforts format
power_data = peak_efforts.get('5min')
if isinstance(power_data, dict):
    power = power_data.get('power', 0)  # New: {power: 350, hr: 160}
else:
    power = power_data  # Old: just 350
```

## When You Get Stuck

1. **Check Recent Conversation Summary** - Understanding of previous fixes
2. **Review Database Schema** - See [database-schema.md](../architecture/database-schema.md)
3. **Look at Similar Code** - Find existing patterns in codebase
4. **Check Git History** - `git log --oneline | head -20`
5. **Test in Isolation** - Create small test script to verify logic
6. **Ask Clarifying Questions** - Better to ask than break prod

## Next Steps

- Read [Database Schema Documentation](../architecture/database-schema.md)
- Review [Streamlit App Structure](../architecture/streamlit-app.md)
- Understand [Development Workflow](./development-workflow.md)
- Learn about [Testing Standards](./testing-guide.md)
