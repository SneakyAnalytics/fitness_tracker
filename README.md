# Fitness Tracker

A comprehensive fitness tracking application with Zwift workout generation, FIT file parsing, and training analytics.

## Features

- **FIT File Processing**: Parse and analyze Garmin/cycling computer data
- **Dynamic Zwift Workout Generation**: Generate .zwo workout files with:
  - Accurate power calculations using explicit FTP values
  - Fresh, API-driven motivational content (quotes, cycling facts, humor)
  - Context-aware messaging (recovery vs. intensity workouts)
  - Anti-repetition logic for varied workout experiences
- **Training Analytics**: Track TSS, power zones, and training load
- **Weekly Planning**: Process structured training plans with automatic FTP detection
- **API & Web Interface**: RESTful API and Streamlit dashboard

## Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/SneakyAnalytics/fitness_tracker.git
   cd fitness_tracker
   ```

2. **Create virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure paths** (optional):

   ```bash
   cp .env.example .env
   # Edit .env with your specific paths
   ```

5. **Initialize database**:
   ```bash
   mkdir -p data
   # Database will be created automatically on first run
   ```

## Usage

### API Server

```bash
uvicorn src.api.app:app --reload
```

### Web Interface

```bash
streamlit run src/ui/streamlit_app.py
```

### Process Workout Plans

```python
from src.utils.proposed_workouts_processor import process_proposed_workouts
process_proposed_workouts('path/to/workout_plan.json')
```

## Workout Plan JSON Format

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
    "weekFocus": "Race preparation",
    "specialConsiderations": "Recovery focused"
  },
  "days": [
    {
      "dayNumber": 1,
      "date": "2025-11-10",
      "workouts": [
        {
          "type": "bike",
          "name": "Recovery Spin",
          "plannedDuration": 45,
          "intervals": [
            {
              "name": "Warm-up",
              "duration": 600,
              "powerTarget": {
                "min": 150,
                "max": 170,
                "unit": "watts"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

## Configuration

Set these environment variables in `.env`:

- `ZWIFT_WORKOUTS_DIR`: Path to Zwift workouts folder (default: `~/Documents/Zwift/Workouts/6870291`)
- `DB_PATH`: Database file path (default: `data/fitness_data.db`)

## Development

Run tests:

```bash
pytest
```

## License

MIT License
