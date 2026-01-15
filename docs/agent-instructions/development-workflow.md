# Development Workflow Guide

## Overview

This guide explains the development workflow for the fitness tracker application, from making code changes to deploying them to the production Beelink server.

## Development Environment Setup

### Prerequisites

- Python 3.12+
- Docker Desktop
- Git
- SSH access to Beelink (for deployment)
- Environment variables configured in `.env`

### Local Development Setup

```bash
# Clone repository
cd /Users/jacobrobinson/fitness_tracker

# Create/activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env  # Edit with your API keys

# Test database access
sqlite3 data/fitness_data.db "SELECT COUNT(*) FROM workouts;"
```

### Docker Development Setup

```bash
# Build and start containers
docker compose build
docker compose up -d

# Verify containers running
docker ps

# Check logs
docker logs fitness-tracker-api
docker logs fitness-tracker-ui

# Access application
# API: http://localhost:8000
# UI: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

## Git Workflow

### Branch Strategy

**Main Branch:**

- `main` - Production-ready code running on Beelink
- Always deployable
- Protected (no direct pushes)

**Feature Branches:**

- `feature/ai-coach-improvements` - New features
- `fix/workout-matching-bug` - Bug fixes
- `docs/update-readme` - Documentation changes
- `refactor/database-cleanup` - Code refactoring

### Commit Message Format

```bash
# Format: <type>: <short description>
#
# Types: feat, fix, docs, refactor, test, chore

# Examples:
git commit -m "feat: Add VO2max interval detection"
git commit -m "fix: Resolve FIT file parsing error for multi-lap workouts"
git commit -m "docs: Update database schema documentation"
git commit -m "refactor: Simplify interval classification logic"
git commit -m "test: Add unit tests for ZwiftWorkoutGenerator"
git commit -m "chore: Update dependencies to latest versions"
```

### Feature Development Flow

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/new-power-zones

# 2. Make changes
# ... edit code ...

# 3. Test locally (see Testing section below)
docker compose down
docker compose up -d
# ... verify changes work ...

# 4. Commit changes
git add .
git commit -m "feat: Add custom power zone configuration"

# 5. Push to remote (if using remote repo)
git push origin feature/new-power-zones

# 6. Merge to main (after testing)
git checkout main
git merge feature/new-power-zones

# 7. Deploy to Beelink (see Deployment section)
./sync_to_beelink.sh 100.117.194.8
```

## Making Code Changes

### Step-by-Step Process

**1. Identify What Needs to Change**

```python
# Example: Adding new endpoint to API

# Read existing code
vim src/api/app.py  # Or use your preferred editor

# Find similar patterns
grep -r "@app.get" src/api/

# Check database requirements
sqlite3 data/fitness_data.db ".schema workouts"
```

**2. Create Feature Branch**

```bash
git checkout -b feature/add-personal-bests-endpoint
```

**3. Make Changes with Documentation**

```python
# src/api/app.py

@app.get("/personal-bests/{athlete_id}")
async def get_personal_bests(athlete_id: str):
    """
    Get personal best efforts for an athlete.

    Args:
        athlete_id: Athlete identifier (default: "default")

    Returns:
        dict: Personal bests for various durations

    Example:
        GET /personal-bests/default
        Returns: {"5s": 450, "1min": 380, "5min": 300, ...}
    """
    db = WorkoutDatabase()

    # Query personal_bests table
    results = db.conn.execute("""
        SELECT effort_type, effort_value
        FROM personal_bests
        WHERE athlete_id = ? AND rank = 1
        ORDER BY effort_type
    """, (athlete_id,)).fetchall()

    # Format response
    personal_bests = {row[0]: row[1] for row in results}
    return personal_bests
```

**4. Update Related Documentation**

```bash
# Update API documentation
vim docs/architecture/api-endpoints.md

# Add example to getting started guide if needed
vim docs/agent-instructions/getting-started.md
```

**5. Test Changes Locally**

```bash
# Restart containers to pick up changes
docker compose down
docker compose build
docker compose up -d

# Test new endpoint
curl http://localhost:8000/personal-bests/default

# Test UI integration if applicable
open http://localhost:8501
# Navigate to relevant tab and verify functionality
```

**6. Commit with Clear Message**

```bash
git add src/api/app.py docs/architecture/api-endpoints.md
git commit -m "feat: Add personal bests API endpoint

- Add GET /personal-bests/{athlete_id} endpoint
- Returns all rank=1 efforts for athlete
- Update API documentation with example
- Tested with curl and Streamlit UI"
```

## Testing Workflow

### Pre-Deployment Testing Checklist

**1. Syntax and Import Validation**

```bash
# Check Python syntax
python3 -m py_compile src/api/app.py
python3 -m py_compile src/ui/streamlit_app.py

# Check for import errors
docker compose up -d
docker logs fitness-tracker-api 2>&1 | grep -i "error\|exception"
docker logs fitness-tracker-ui 2>&1 | grep -i "error\|exception"
```

**2. API Testing**

```bash
# Health check
curl http://localhost:8000/health

# Test specific endpoints
curl http://localhost:8000/workouts?start_date=2026-01-01&end_date=2026-01-31

# Test POST requests
curl -X POST http://localhost:8000/ai-coach/generate-weekly-plan \
  -H "Content-Type: application/json" \
  -d '{"week_number": 61, "start_date": "2026-01-12", "planned_tss_min": 300, "planned_tss_max": 400}'
```

**3. UI Testing**

```bash
# Open in browser
open http://localhost:8501

# Manual testing checklist:
# [ ] Login page works
# [ ] Dashboard loads with recent workouts
# [ ] Calendar displays correctly
# [ ] AI Coach tab generates plans
# [ ] Workout tracking forms submit
# [ ] Analytics charts render
# [ ] No console errors (open browser dev tools)
```

**4. Database Testing**

```bash
# Verify database changes
sqlite3 data/fitness_data.db

sqlite> SELECT COUNT(*) FROM workouts;
sqlite> SELECT * FROM workouts ORDER BY workout_day DESC LIMIT 5;
sqlite> .schema workout_analyses
sqlite> .exit
```

**5. Integration Testing**

```bash
# Full workflow test: Sync → Analyze → Coach
python3 scripts/sync_trainingpeaks.py --date 2026-01-15
# Verify workout appears in database

# Analyze workout
curl -X POST http://localhost:8000/analyze-workout \
  -H "Content-Type: application/json" \
  -d '{"workout_id": 123}'
# Verify analysis created

# Generate weekly plan
# Use AI Coach tab in UI
# Verify plan appears in weekly_plans table
```

### Running Unit Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_fit_parser_and_athlete_settings.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v tests/
```

### Manual Test Scripts

Create test scripts for complex workflows:

```python
# test_workflow.py
"""Test complete workout sync and analysis workflow"""

import sys
sys.path.append(".")

from src.storage.database import WorkoutDatabase
from src.utils.interval_detector import IntervalDetector
import requests

def test_workflow():
    db = WorkoutDatabase()

    # 1. Check for recent workouts
    workouts = db.conn.execute("""
        SELECT id, workout_day, workout_title
        FROM workouts
        ORDER BY workout_day DESC
        LIMIT 5
    """).fetchall()

    print(f"✓ Found {len(workouts)} recent workouts")

    # 2. Check for FIT files
    fit_files = db.conn.execute("""
        SELECT COUNT(*) FROM fit_files
    """).fetchone()[0]

    print(f"✓ Found {fit_files} FIT files")

    # 3. Test API health
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200
    print("✓ API health check passed")

    # 4. Test interval detection
    ftp = db.get_athlete_setting('ftp') or 300
    detector = IntervalDetector(ftp=ftp)
    print(f"✓ Interval detector initialized with FTP={ftp}")

    print("\n✅ All workflow tests passed!")

if __name__ == "__main__":
    test_workflow()
```

Run test script:

```bash
python3 test_workflow.py
```

## Deployment Workflow

### Deployment to Beelink (Production)

**Method 1: Using Sync Script + Manual Restart (Recommended)**

```bash
cd /Users/jacobrobinson/fitness_tracker

# Sync files to Beelink (Windows rsync)
./sync_to_beelink.sh 100.117.194.8

# SSH to Beelink and restart containers (Windows commands)
ssh rakej@100.117.194.8
# On Beelink Windows:
cd C:\Users\rakej\fitness_tracker
docker compose down
docker compose up -d
docker ps
exit

# Verify deployment from Mac
curl http://100.117.194.8:8000/health
curl -I http://100.117.194.8:8501
```

**Method 2: Manual Deployment (Individual Files)**

```bash
# From Mac - SCP specific files to Beelink Windows
# Note: Use /c/ path format for Windows C:\ in SCP
scp src/api/app.py rakej@100.117.194.8:/c/Users/rakej/fitness_tracker/src/api/

# SSH to Beelink and restart specific container
ssh rakej@100.117.194.8
cd C:\Users\rakej\fitness_tracker
docker compose restart fitness-tracker-api
docker logs fitness-tracker-api --tail 20
exit
```

**Method 3: Full Rebuild (For Major Changes)**

```bash
ssh rakej@100.117.194.8

# On Beelink:
cd C:\Users\rakej\fitness_tracker
docker compose down
docker compose build --no-cache
docker compose up -d
docker ps  # Verify both containers running
exit
```

### Post-Deployment Verification

```bash
# Check container status
ssh rakej@100.117.194.8 "docker ps"

# Check logs for errors
ssh rakej@100.117.194.8 "docker logs fitness-tracker-ui --tail 50"
ssh rakej@100.117.194.8 "docker logs fitness-tracker-api --tail 50"

# Test API remotely
curl http://100.117.194.8:8000/health

# Test UI remotely
curl -I http://100.117.194.8:8501  # Should return 200

# Test from iPhone via Tailscale
# Open: http://100.117.194.8:8501
```

### Rollback Procedure

If deployment causes issues:

```bash
# 1. SSH to Beelink
ssh rakej@100.117.194.8

# 2. Revert to previous code (if using git)
cd C:\Users\rakej\fitness_tracker
git log --oneline -5  # Find previous commit
git checkout <previous-commit-hash>

# 3. Rebuild and restart
docker compose down
docker compose build
docker compose up -d

# 4. Verify rollback successful
docker ps
docker logs fitness-tracker-ui --tail 20
exit

# 5. Test from Mac
curl http://100.117.194.8:8501
```

Or restore from backup:

```bash
ssh rakej@100.117.194.8

# Restore database backup (if needed)
cd C:\Users\rakej\fitness_tracker\data
copy fitness_data.db.backup fitness_data.db

# Restore code from previous sync (Mac side)
# On Mac:
git checkout <previous-commit>
./sync_to_beelink.sh 100.117.194.8
```

## Common Development Tasks

### Adding a New API Endpoint

```python
# 1. Define endpoint in src/api/app.py
@app.get("/api/new-endpoint")
async def new_endpoint(param: str):
    """Docstring explaining endpoint"""
    db = WorkoutDatabase()
    # ... implementation ...
    return {"result": "data"}

# 2. Test locally
curl http://localhost:8000/api/new-endpoint?param=value

# 3. Update docs/architecture/api-endpoints.md
# 4. Deploy to Beelink
```

### Adding a New Streamlit Tab

```python
# 1. Edit src/ui/streamlit_app.py
# Find main tab creation section (around line 3800)

# Add new tab
tab1, tab2, tab3, tab_new = st.tabs(["📊 Dashboard", "📅 Calendar", "🤖 AI Coach", "🆕 New Feature"])

# 2. Create tab content function
def display_new_feature():
    st.header("🆕 New Feature")
    # ... tab content ...

# 3. Call function in tab context
with tab_new:
    display_new_feature()

# 4. Test locally with docker compose restart
# 5. Deploy to Beelink
```

### Modifying Database Schema

```python
# 1. Create migration script
# migrations/add_new_column.py

import sqlite3

def migrate():
    conn = sqlite3.connect('data/fitness_data.db')

    # Create backup first
    conn.execute("CREATE TABLE workouts_backup AS SELECT * FROM workouts")

    # Add new column
    conn.execute("ALTER TABLE workouts ADD COLUMN new_field TEXT")

    conn.commit()
    conn.close()
    print("✓ Migration complete")

if __name__ == "__main__":
    migrate()

# 2. Run migration locally
python3 migrations/add_new_column.py

# 3. Test application still works
docker compose restart

# 4. Update database-schema.md documentation

# 5. Run migration on Beelink
scp migrations/add_new_column.py rakej@100.117.194.8:/c/Users/rakej/fitness_tracker/migrations/
ssh rakej@100.117.194.8 "cd C:\Users\rakej\fitness_tracker && python migrations/add_new_column.py"
```

### Adding a New Utility Function

```python
# 1. Choose appropriate file in src/utils/
# - interval_detector.py - Interval detection logic
# - zwift_workout_generator.py - Zwift file generation
# - ai_coach_utils.py - AI coaching helpers
# Or create new file for new category

# 2. Add function with documentation
def calculate_variability_index(normalized_power: float, average_power: float) -> float:
    """
    Calculate Variability Index (VI) for a workout.

    VI = Normalized Power / Average Power
    - VI < 1.05: Steady effort
    - VI 1.05-1.10: Moderate variability
    - VI > 1.10: High variability

    Args:
        normalized_power: NP in watts
        average_power: Average power in watts

    Returns:
        Variability Index as float
    """
    if average_power == 0:
        return 0.0
    return normalized_power / average_power

# 3. Add unit tests
# tests/test_utils.py

def test_calculate_variability_index():
    assert calculate_variability_index(300, 300) == 1.0
    assert calculate_variability_index(315, 300) == 1.05
    assert calculate_variability_index(0, 300) == 0.0  # Edge case

# 4. Run tests
pytest tests/test_utils.py -v
```

## Debugging Workflow

### Debugging API Issues

```bash
# 1. Check API logs
docker logs fitness-tracker-api --tail 100

# 2. Enable verbose logging (if needed)
# Edit docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG

docker compose restart fitness-tracker-api

# 3. Use FastAPI interactive docs
open http://localhost:8000/docs
# Test endpoints directly in Swagger UI

# 4. Add print debugging
# src/api/app.py
@app.get("/workouts")
async def get_workouts(start_date: str, end_date: str):
    print(f"DEBUG: Querying workouts from {start_date} to {end_date}")
    # ... rest of code ...
    print(f"DEBUG: Found {len(workouts)} workouts")
    return workouts

# 5. Restart and check logs
docker compose restart fitness-tracker-api
docker logs fitness-tracker-api --follow
```

### Debugging Streamlit Issues

```bash
# 1. Check UI logs
docker logs fitness-tracker-ui --tail 100

# 2. Run Streamlit locally (not in Docker)
source venv/bin/activate
streamlit run src/ui/streamlit_app.py
# Errors will appear in terminal with full stack traces

# 3. Add st.write() debugging
# src/ui/streamlit_app.py
st.write("DEBUG: session_state =", st.session_state)
st.write("DEBUG: selected_workout =", workout)

# 4. Check browser console
# Open browser dev tools (F12)
# Look for JavaScript errors or network failures
```

### Debugging Database Issues

```bash
# 1. Access database directly
sqlite3 data/fitness_data.db

sqlite> .tables
sqlite> .schema workouts
sqlite> SELECT COUNT(*) FROM workouts;
sqlite> SELECT * FROM workouts ORDER BY workout_day DESC LIMIT 5;

# 2. Check for corrupted data
sqlite> PRAGMA integrity_check;

# 3. View recent changes
sqlite> SELECT * FROM sqlite_sequence;  # Check auto-increment values

# 4. Test specific queries
sqlite> EXPLAIN QUERY PLAN SELECT * FROM workouts WHERE workout_day = '2026-01-15';

# 5. Export for inspection
sqlite> .mode csv
sqlite> .output workouts.csv
sqlite> SELECT * FROM workouts;
sqlite> .exit

# 6. View CSV
cat workouts.csv
```

## Code Review Checklist

Before merging to main:

- [ ] Code follows existing patterns (see [getting-started.md](./getting-started.md#common-code-patterns))
- [ ] Functions have docstrings
- [ ] No hardcoded paths (use environment variables)
- [ ] Error handling added for new code
- [ ] Database queries use parameterized statements (SQL injection prevention)
- [ ] No sensitive data in code (use environment variables)
- [ ] Tests pass locally (`pytest tests/`)
- [ ] Docker containers build successfully
- [ ] API endpoints tested with curl
- [ ] UI changes tested in browser
- [ ] Documentation updated in `docs/`
- [ ] Commit message follows format
- [ ] Changes deployed and tested on Beelink

## Performance Optimization

### Database Query Optimization

```python
# ❌ BAD: N+1 query problem
workouts = db.get_all_workouts()
for workout in workouts:
    fit_file = db.get_fit_file(workout['fit_file_id'])  # N queries!

# ✅ GOOD: JOIN query
workouts_with_fits = db.conn.execute("""
    SELECT w.*, f.fit_data
    FROM workouts w
    LEFT JOIN fit_files f ON w.fit_file_id = f.id
    WHERE w.workout_day >= ?
""", (start_date,)).fetchall()
```

### Caching Expensive Operations

```python
import functools

@functools.lru_cache(maxsize=128)
def get_athlete_ftp():
    """Cache FTP lookups"""
    db = WorkoutDatabase()
    return db.get_athlete_setting('ftp') or 300
```

### Streamlit Performance

```python
# Use st.cache_data for expensive computations
@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_workout_data(start_date, end_date):
    response = requests.get(f"{API_URL}/workouts", params={
        "start_date": start_date,
        "end_date": end_date
    })
    return response.json()
```

## Next Steps

- **Testing Guide**: [testing-guide.md](./testing-guide.md) - Comprehensive testing strategies
- **Database Schema**: [../architecture/database-schema.md](../architecture/database-schema.md) - Understand data structure
- **API Endpoints**: [../architecture/api-endpoints.md](../architecture/api-endpoints.md) - Available backend endpoints
