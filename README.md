# Fitness Tracker

A comprehensive AI-powered fitness tracking system with automated TrainingPeaks sync, workout analysis, and Zwift integration.

## 🌟 Key Features

### 🤖 Automated Daily Workflow

- **TrainingPeaks Auto-Sync**: Headless browser automation logs in, downloads workouts
- **AI Analysis**: Gemini-powered workout insights and peak effort detection
- **Personal Best Tracking**: Medal system (🥇🥈🥉) for 7 effort durations
- **Auto-Cleanup**: Removes temporary files after processing
- **10pm PST Scheduling**: Runs automatically via cron job

### 💪 AI Workout Generation

- **Claude-Powered Planning**: Uses Haiku for analysis + Sonnet for generation
- **Weekly Plans**: Structured workouts based on your fitness data and goals
- **Zwift File Export**: Auto-generates .zwo files with dynamic alerts

### 📊 Workout Analysis

- **FIT File Parsing**: Complete power, HR, cadence data extraction
- **Peak Efforts**: 30s, 1min, 3min, 5min, 10min, 20min, 60min
- **AI Insights**: Quality ratings, recovery recommendations, training suggestions
- **Interactive Graphs**: Power curves, zone distribution, multi-panel dashboards

### 🚴 Zwift Integration

- **Dynamic Content**: API-based jokes, facts, trivia, cycling tips
- **Zero Repetition**: Never see the same message twice
- **Smart Spacing**: 10-15 messages evenly distributed per workout
- **Trivia Split**: Questions followed by answers 60s later

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

   # Install Playwright browsers (required for TrainingPeaks automation)
   playwright install chromium
   ```

4. **Configure environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

   **Required variables:**

   ```bash
   TRAININGPEAKS_USERNAME=your_email@example.com
   TRAININGPEAKS_PASSWORD=your_password
   GEMINI_API_KEY=your_gemini_key

   # Optional
   ANTHROPIC_API_KEY=your_claude_key
   ZWIFT_WORKOUTS_DIR=~/Documents/Zwift/Workouts/6870291
   ```

5. **Initialize database**:
   ```bash
   mkdir -p data logs
   # Database will be created automatically on first run
   ```

## 🚀 Quick Start

### 1. Automated Daily Workflow (Recommended)

Set up automatic TrainingPeaks sync & analysis at 10pm PST:

```bash
# Run setup script
./setup_daily_automation.sh

# Add to crontab (edit with: crontab -e)
0 22 * * * cd /path/to/fitness_tracker && /path/to/venv/bin/python -m src.utils.daily_auto_sync_and_analyze >> logs/daily_automation.log 2>&1
```

**What it does every day:**

1. 🔄 Logs into TrainingPeaks at 10pm
2. 📥 Downloads today's workout files
3. 💾 Stores in database
4. 🤖 Runs AI analysis with Gemini
5. 🏅 Updates personal bests
6. 🧹 Cleans up temp files

### 2. Manual Run (Streamlit UI)

```bash
# Start API server (terminal 1)
uvicorn src.api.app:app --reload

# Start web interface (terminal 2)
streamlit run src/ui/streamlit_app.py
```

Then navigate to:

- **Performance Analytics** → Auto Analysis → "Run Analysis Now"
- **AI Coaching** → Generate weekly workout plans
- **Zwift Generator** → Create workout files with dynamic alerts

### 3. Command Line Usage

```bash
# Run today's automation
python -m src.utils.daily_auto_sync_and_analyze

# Run for specific date
python -m src.utils.daily_auto_sync_and_analyze 2025-11-18

# Weekly TrainingPeaks sync (full week)
python -m src.utils.trainingpeaks_sync
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

## ⚙️ Configuration

Create a `.env` file with your credentials:

```bash
# Required for TrainingPeaks automation
TRAININGPEAKS_USERNAME=your_email@example.com
TRAININGPEAKS_PASSWORD=your_password

# Required for AI analysis
GEMINI_API_KEY=your_gemini_api_key

# Optional: Claude AI for workout generation
ANTHROPIC_API_KEY=your_anthropic_key

# Optional: Custom paths
ZWIFT_WORKOUTS_DIR=~/Documents/Zwift/Workouts/6870291
DB_PATH=data/fitness_data.db
```

**Cost Estimate:**

- **Gemini (Analysis)**: $0.0001-0.0003 per workout (~$0.02/week)
- **Claude (Generation)**: Haiku ($0.008) + Sonnet ($0.156) = $0.164/week
- **Total**: ~$0.18/week for full automation

## 📂 Project Structure

```
fitness_tracker/
├── src/
│   ├── api/                    # FastAPI server
│   ├── models/                 # Data models
│   ├── storage/                # Database layer
│   ├── ui/                     # Streamlit interface
│   └── utils/
│       ├── daily_auto_sync_and_analyze.py    # Main automation
│       ├── trainingpeaks_sync.py             # TP browser automation
│       ├── fit_file_analyzer.py              # AI workout analysis
│       ├── ai_coach_engine.py                # Workout generation
│       ├── zwift_workout_generator.py        # .zwo file creation
│       └── dynamic_workout_content.py        # API-based alerts
├── data/                       # Database & workout files
├── logs/                       # Automation logs
├── archive/                    # Old documentation
├── setup_daily_automation.sh   # Setup script
└── README.md                   # This file
```

## Development

Run tests:

```bash
pytest
```

## License

MIT License
