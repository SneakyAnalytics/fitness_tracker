# FastAPI Endpoints Documentation

## Overview

The FastAPI backend provides RESTful endpoints for workout management, AI analysis, weekly planning, and Zwift integration. The API runs on port 8000 and provides interactive documentation at `/docs`.

**Base URL:**

- Local: `http://localhost:8000`
- Production (Beelink): `http://100.117.194.8:8000`
- Interactive Docs: `http://localhost:8000/docs`

**Authentication:** Currently no authentication (password protection at Streamlit UI level)

---

## Health & Status

### `GET /`

Root endpoint - simple status check.

**Response:**

```json
{
  "message": "Fitness Tracker API is running"
}
```

**Example:**

```bash
curl http://localhost:8000/
```

### `GET /health`

Comprehensive health check for monitoring and troubleshooting.

**Response:**

```json
{
  "status": "healthy",
  "database": {
    "exists": true,
    "accessible": true,
    "path": "data/fitness_data.db"
  },
  "environment": {
    "has_anthropic_key": true,
    "has_google_key": true,
    "has_tp_username": true
  },
  "message": "Fitness Tracker API is running"
}
```

**Status Values:**

- `"healthy"` - All systems operational
- `"degraded"` - Database issues or missing environment variables

**Example:**

```bash
curl http://localhost:8000/health
```

**Use Cases:**

- Container health checks
- Monitoring/alerting systems
- Troubleshooting deployment issues
- Verifying environment configuration

---

## Workout Endpoints

### `GET /workouts`

Get all workouts from the database.

**Response:**

```json
[
  {
    "id": 123,
    "workout_day": "2026-01-14",
    "workout_title": "Threshold Development 2x15min",
    "workout_data": "{\"type\":\"Bike\",\"duration\":3600,\"tss\":85}",
    "athlete_comments": "Felt strong, held power well",
    "sequence_number": 1,
    "fit_file_id": 456
  }
]
```

**Example:**

```bash
curl http://localhost:8000/workouts
```

### `GET /workouts/with-analyses`

Get all workouts with their AI analyses and interval data.

**Response:**

```json
[
  {
    "id": 123,
    "workout_day": "2026-01-14",
    "workout_title": "Threshold Development 2x15min",
    "workout_data": "{...}",
    "analysis_text": "Excellent threshold workout...",
    "analysis_data": "{\"intervals\":[...],\"peak_efforts\":{...}}"
  }
]
```

**Example:**

```bash
curl http://localhost:8000/workouts/with-analyses
```

### `GET /workouts/week`

Get all workouts for a specific week.

**Query Parameters:**

- `start_date` (required): Week start date (YYYY-MM-DD format)

**Response:**

```json
[
  {
    "id": 123,
    "workout_day": "2026-01-14",
    "workout_title": "Threshold Development 2x15min",
    "workout_data": "{...}"
  }
]
```

**Example:**

```bash
curl "http://localhost:8000/workouts/week?start_date=2026-01-12"
```

### `POST /workouts/qualitative`

Add qualitative feedback to a workout.

**Request Body:**

```json
{
  "workout_id": 123,
  "how_it_felt": "Strong, maintained power throughout",
  "technical_issues": "HR strap disconnected briefly",
  "modifications": "Extended warmup by 5 minutes",
  "athlete_comments": "Ready for race day"
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Qualitative data saved"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/workouts/qualitative \
  -H "Content-Type: application/json" \
  -d '{"workout_id": 123, "how_it_felt": "Strong", "athlete_comments": "Great session"}'
```

---

## Upload Endpoints

### `POST /upload/workouts`

Upload workout data (CSV format from TrainingPeaks).

**Request Body:**

```json
{
  "csv_content": "Date,Workout Name,Duration,...\n2026-01-14,Threshold...",
  "date": "2026-01-14"
}
```

**Response:**

```json
{
  "status": "success",
  "message": "2 workouts uploaded successfully"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/upload/workouts \
  -H "Content-Type: application/json" \
  -d '{"csv_content": "Date,Workout Name,...", "date": "2026-01-14"}'
```

### `POST /upload/fit`

Upload and analyze FIT file.

**Request:** Multipart form with FIT file

**Response:**

```json
{
  "status": "success",
  "fit_file_id": 456,
  "analysis": {
    "intervals": [...],
    "peak_efforts": {...},
    "summary": "Excellent threshold workout..."
  }
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/upload/fit \
  -F "file=@workout.fit"
```

### `POST /upload/metrics`

Upload daily metrics (sleep, HRV, etc.).

**Request Body:**

```json
{
  "date": "2026-01-14",
  "metric_type": "sleep",
  "metric_data": {
    "hours": 7.5,
    "quality": "good",
    "hrv": 65
  }
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Metrics saved"
}
```

### `POST /upload/proposed_workouts`

Upload proposed workouts for a week (from AI coach).

**Request Body:**

```json
{
  "week_number": 61,
  "start_date": "2026-01-12",
  "workouts": [
    {
      "day_number": 1,
      "date": "2026-01-12",
      "type": "bike",
      "name": "Threshold Development 2x15min",
      "planned_duration": 3600,
      "planned_tss_min": 80,
      "planned_tss_max": 90,
      "intervals": {...}
    }
  ]
}
```

**Response:**

```json
{
  "status": "success",
  "message": "7 workouts uploaded for week 61"
}
```

---

## AI Coach & Planning

### `GET /proposed_workouts/week`

Get proposed workouts for a specific week.

**Query Parameters:**

- `week_number` (required): Week number (1-52)

**Response:**

```json
[
  {
    "id": 789,
    "dailyPlanId": 101,
    "type": "bike",
    "name": "Threshold Development 2x15min",
    "plannedDuration": 3600,
    "plannedTSS_min": 80,
    "plannedTSS_max": 90,
    "intervals": {...},
    "notes": "Focus on steady power"
  }
]
```

**Example:**

```bash
curl "http://localhost:8000/proposed_workouts/week?week_number=61"
```

---

## Summary Endpoints

### `GET /summaries`

Get all weekly summaries.

**Response:**

```json
[
  {
    "id": 1,
    "start_date": "2026-01-12",
    "end_date": "2026-01-18",
    "summary_data": "Strong week with 400 TSS...",
    "qualitative_data": "{...}"
  }
]
```

**Example:**

```bash
curl http://localhost:8000/summaries
```

### `GET /summary/generate`

Generate AI weekly summary.

**Query Parameters:**

- `start_date` (required): Week start date (YYYY-MM-DD)
- `end_date` (required): Week end date (YYYY-MM-DD)

**Response:**

```json
{
  "summary": "This week you completed 6 workouts totaling 420 TSS...",
  "total_tss": 420,
  "total_training_hours": 8.5,
  "sessions_completed": 6,
  "workout_types": ["bike", "strength", "mobility"]
}
```

**Example:**

```bash
curl "http://localhost:8000/summary/generate?start_date=2026-01-12&end_date=2026-01-18"
```

### `POST /summary/save`

Save weekly summary with qualitative data.

**Request Body:**

```json
{
  "start_date": "2026-01-12",
  "end_date": "2026-01-18",
  "total_tss": 420,
  "total_training_hours": 8.5,
  "sessions_completed": 6,
  "daily_energy": {
    "2026-01-12": 7,
    "2026-01-13": 8
  },
  "daily_sleep_quality": {
    "2026-01-12": 8,
    "2026-01-13": 7
  },
  "muscle_soreness_patterns": {
    "legs": {"severity": 6, "notes": "Quads tight"}
  },
  "general_fatigue_level": 5,
  "qualitative_feedback": [...]
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Summary saved"
}
```

### `GET /summary/export`

Export weekly summary as text file.

**Query Parameters:**

- `start_date` (required): Week start date
- `end_date` (required): Week end date

**Response:**

```json
{
  "content": "WEEKLY SUMMARY\nJan 12-18, 2026\n\nTotal TSS: 420\n..."
}
```

---

## Athlete Settings

### `GET /athlete/settings`

Get athlete settings (FTP, zones, preferences).

**Query Parameters:**

- `athlete_id` (optional): Default is "default"

**Response:**

```json
{
  "athlete_id": "default",
  "ftp": 300,
  "weight_kg": 75,
  "max_hr": 185,
  "zones": {
    "z1": [0, 0.55],
    "z2": [0.56, 0.75],
    "z3": [0.76, 0.9],
    "z4": [0.91, 1.05],
    "z5": [1.06, 1.2]
  }
}
```

**Example:**

```bash
curl http://localhost:8000/athlete/settings
```

### `POST /athlete/settings`

Update athlete settings.

**Request Body:**

```json
{
  "athlete_id": "default",
  "ftp": 310,
  "weight_kg": 75,
  "max_hr": 185
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Settings updated"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/athlete/settings \
  -H "Content-Type: application/json" \
  -d '{"athlete_id": "default", "ftp": 310}'
```

---

## Zwift Integration

### `GET /zwift/generate_workouts`

Generate Zwift .zwo files for a week.

**Query Parameters:**

- `week_number` (required): Week number to generate
- `output_dir` (optional): Custom output directory

**Response:**

```json
{
  "status": "success",
  "files_generated": 5,
  "output_dir": "/Users/username/Documents/Zwift/Workouts/6870291/Week_61",
  "files": [
    "2026_01_12_Threshold_Development_2x15min.zwo",
    "2026_01_14_VO2max_Intervals_3x5min.zwo"
  ]
}
```

**Example:**

```bash
curl "http://localhost:8000/zwift/generate_workouts?week_number=61"
```

**Generated .zwo Structure:**

```xml
<workout_file>
  <name>Threshold Development 2x15min</name>
  <description>Focus on steady threshold power</description>
  <sportType>bike</sportType>
  <workout>
    <Warmup Duration="600" PowerLow="0.5" PowerHigh="0.65"/>
    <SteadyState Duration="900" Power="0.95"/>
    <Cooldown Duration="600" PowerLow="0.65" PowerHigh="0.5"/>
  </workout>
</workout_file>
```

---

## Performance Tracking

### `POST /workout/performance`

Save workout performance data.

**Request Body:**

```json
{
  "workout_id": 123,
  "workout_date": "2026-01-14",
  "actual_duration": 3600,
  "performance_data": {
    "avg_power": 285,
    "normalized_power": 290,
    "avg_hr": 165,
    "tss": 85,
    "completed": true
  }
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Performance data saved"
}
```

### `GET /workout/performance`

Get performance data for a workout.

**Query Parameters:**

- `workout_id` (required): Workout ID

**Response:**

```json
{
  "id": 1,
  "workout_id": 123,
  "workout_date": "2026-01-14",
  "actual_duration": 3600,
  "performance_data": {...}
}
```

---

## Debug Endpoints

### `POST /debug/workout_upload`

Debug endpoint for troubleshooting workout uploads.

**Request Body:**

```json
{
  "workout_data": {...},
  "debug": true
}
```

**Response:**

```json
{
  "status": "debug",
  "parsed_data": {...},
  "validation_errors": [],
  "database_state": {...}
}
```

---

## Error Responses

All endpoints follow consistent error response format:

### 400 Bad Request

```json
{
  "detail": "Invalid date format. Use YYYY-MM-DD"
}
```

### 404 Not Found

```json
{
  "detail": "Workout not found with id: 123"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Database connection failed: ..."
}
```

---

## Common Usage Patterns

### 1. Check API Health

```bash
# Quick check
curl http://localhost:8000/

# Detailed health check
curl http://localhost:8000/health | jq
```

### 2. Get Week's Workouts

```bash
# Get all workouts for a week
curl "http://localhost:8000/workouts/week?start_date=2026-01-12" | jq

# Get proposed workouts for planning
curl "http://localhost:8000/proposed_workouts/week?week_number=61" | jq
```

### 3. Generate Weekly Summary

```bash
# Generate AI summary
curl "http://localhost:8000/summary/generate?start_date=2026-01-12&end_date=2026-01-18" | jq '.summary'

# Save with qualitative data
curl -X POST http://localhost:8000/summary/save \
  -H "Content-Type: application/json" \
  -d @weekly_summary.json
```

### 4. Update FTP

```bash
curl -X POST http://localhost:8000/athlete/settings \
  -H "Content-Type: application/json" \
  -d '{"ftp": 310}'
```

### 5. Generate Zwift Workouts

```bash
# Generate for week 61
curl "http://localhost:8000/zwift/generate_workouts?week_number=61" | jq '.files'
```

---

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

**Swagger UI:**

- URL: `http://localhost:8000/docs`
- Features: Try endpoints directly in browser, see request/response schemas

**ReDoc:**

- URL: `http://localhost:8000/redoc`
- Features: Clean documentation layout, better for reading

**OpenAPI Schema:**

- URL: `http://localhost:8000/openapi.json`
- Features: Machine-readable API specification

---

## Testing Endpoints

### Using curl

```bash
# GET request
curl http://localhost:8000/workouts

# POST request with JSON
curl -X POST http://localhost:8000/summary/save \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2026-01-12", "total_tss": 420}'

# POST request with file
curl -X POST http://localhost:8000/upload/fit \
  -F "file=@workout.fit"
```

### Using Python

```python
import requests

# GET request
response = requests.get("http://localhost:8000/workouts")
workouts = response.json()

# POST request
response = requests.post(
    "http://localhost:8000/summary/save",
    json={"start_date": "2026-01-12", "total_tss": 420}
)
print(response.status_code)  # 200 for success
```

### Using httpie

```bash
# GET request
http GET localhost:8000/workouts

# POST request
http POST localhost:8000/summary/save start_date="2026-01-12" total_tss:=420
```

---

## Environment Variables

Required for various endpoints:

```bash
# AI Analysis
ANTHROPIC_API_KEY=sk-ant-...  # Claude for coaching
GOOGLE_API_KEY=AIza...        # Gemini for analysis

# TrainingPeaks Sync
TP_USERNAME=your_email@example.com
TP_PASSWORD=your_password

# Zwift Integration
ZWIFT_WORKOUTS_DIR=/Users/username/Documents/Zwift/Workouts/6870291
```

---

## Rate Limiting & Performance

**Current Implementation:**

- No rate limiting implemented
- Database connection per request
- Async endpoints for better performance

**Best Practices:**

- Use `/health` for monitoring (lightweight)
- Cache athlete settings in client
- Batch workout uploads when possible
- Use query parameters for filtering

---

## Next Steps

- **Database Schema**: [database-schema.md](./database-schema.md) - Understand data structure
- **Streamlit UI**: [streamlit-app.md](./streamlit-app.md) - See how UI calls these endpoints
- **Development**: [../agent-instructions/development-workflow.md](../agent-instructions/development-workflow.md#adding-a-new-api-endpoint) - Add new endpoints
