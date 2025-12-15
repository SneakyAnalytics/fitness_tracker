# 🏃‍♂️ AI-Powered Fitness Tracker

**A comprehensive training system with automated workout sync, AI analysis, intelligent coaching, and Zwift integration.**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Overview

This is an end-to-end fitness tracking and coaching system that:

- **Automatically syncs** workouts from TrainingPeaks (headless browser automation)
- **Analyzes performance** using AI (Gemini) to extract insights from FIT files
- **Tracks personal bests** across 8 effort durations (30s to 60min)
- **Generates weekly training plans** using Claude AI with coaching continuity
- **Creates Zwift workouts** with dynamic, never-repeating entertainment content
- **Provides rich visualizations** in a Streamlit dashboard

**Cost:** ~$2/month (95% cheaper than original implementation using cost-optimized AI models)

---

## ✨ Key Features

### 🤖 Automated Daily Workflow

- **10pm PST Auto-Sync**: Downloads today's workout from TrainingPeaks
- **AI Analysis**: Gemini extracts insights, detects peak efforts, rates workout quality
- **Personal Best Tracking**: Automatically updates PR medals (🥇🥈🥉) for 8 durations
- **Auto-Cleanup**: Removes temporary files after processing
- **Cron Integration**: Runs hands-free every night

### 🧠 AI Coaching with Memory

- **Weekly Analysis**: Claude analyzes your training week with context-aware insights
- **Coaching Continuity**: AI references last 3 weeks of analysis for progressive planning
- **Auto-Updating Profile**: Extracts milestones, goals, and FTP updates from your feedback
- **Intelligent Planning**: Generates periodized workout plans tailored to your goals
- **Pattern Recognition**: Learns your schedule, preferences, and response to training

### 📊 Performance Analytics

- **FIT File Parsing**: Complete power, HR, cadence, GPS data extraction
- **Peak Effort Detection**: 30s, 1min, 3min, 5min, 10min, 20min, 45min, 60min
- **Power Curve Analysis**: Visualize your peak power across all durations
- **Zone Distribution**: Time-in-zone charts for training load analysis
- **Multi-Panel Dashboards**: Interactive graphs with hover details

### 🚴 Zwift Integration

- **Dynamic Content System**: 12 API sources for text alerts
  - Inspirational quotes (Quotable, Affirmations, Kanye)
  - Humor (Dad Jokes, Chuck Norris facts)
  - Knowledge (Fun Facts, Number Facts, Advice)
  - Sports content (Trivia questions/answers)
  - Science/Tech (HackerNews, arXiv papers, Wikipedia Today)
- **Zero Repetition**: API-based content means never seeing same message twice
- **Smart Spacing**: 10-15 messages per workout, evenly distributed
- **Trivia Format**: Question → 45 seconds later → Answer

### 🎯 Smart Features

- **Week-to-Week Memory**: AI coaching continuity across multiple weeks
- **Auto-FTP Updates**: Mention "my FTP is 310W" in feedback → automatically updated
- **Milestone Tracking**: "Completed my first century" → achievement recorded
- **Goal Extraction**: "Aiming for 5-hour rides" → goal added to profile
- **Sentiment Detection**: AI understands "feeling stronger" vs "struggling with"

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **TrainingPeaks account** (for workout sync)
- **Gemini API key** (free tier works: https://makersuite.google.com/app/apikey)
- **Claude API key** (optional, for AI coaching: https://console.anthropic.com/)
- **Zwift account** (optional, for workout file generation)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/fitness_tracker.git
cd fitness_tracker

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers (for TrainingPeaks automation)
playwright install chromium

# 5. Configure environment
cp .env.example .env
# Edit .env with your API keys and credentials
```

### Configuration (.env file)

```bash
# Required for TrainingPeaks sync
TRAININGPEAKS_USERNAME=your_email@example.com
TRAININGPEAKS_PASSWORD=your_password

# Required for AI analysis (FREE TIER WORKS!)
GEMINI_API_KEY=your_gemini_api_key

# Optional: AI Coaching
ANTHROPIC_API_KEY=your_claude_key

# Optional: Custom paths
ZWIFT_WORKOUTS_DIR=~/Documents/Zwift/Workouts/YOUR_ID
DB_PATH=data/fitness_data.db
```

### First Run

```bash
# Initialize database structure
mkdir -p data logs

# Start Streamlit UI
streamlit run src/ui/streamlit_app.py

# Navigate to "Performance Analytics" tab
# Click "Run Analysis Now" to process your first workout
```

---

## 📖 Usage Guide

### Method 1: Automated Daily Workflow (Recommended)

Set up hands-free automation that runs every night at 10pm PST:

```bash
# Run setup script
./setup_daily_automation.sh

# Add to crontab (edit with: crontab -e)
0 22 * * * cd /path/to/fitness_tracker && /path/to/venv/bin/python -m src.utils.daily_auto_sync_and_analyze >> logs/daily_automation.log 2>&1
```

**What happens automatically:**

1. 🔄 Logs into TrainingPeaks (headless browser)
2. 📥 Downloads today's workout FIT file
3. 💾 Stores in SQLite database
4. 🤖 Runs AI analysis with Gemini
5. 🏅 Updates personal best medals
6. 📧 (Optional) Sends summary email
7. 🧹 Cleans up temporary files

**Check logs:**

```bash
tail -f logs/daily_automation.log
tail -f logs/daily_automation.err
```

### Method 2: Streamlit UI (Manual/Interactive)

```bash
# Start application
streamlit run src/ui/streamlit_app.py
```

**Tabs available:**

1. **📊 Performance Analytics**

   - View workout history and statistics
   - Run AI analysis on demand
   - See personal best medals

2. **🤖 AI Weekly Coaching**

   - Generate weekly analysis (reviews past 7 days)
   - Create next week's workout plan
   - Provide feedback (auto-updates coaching notes!)

3. **🚴 Zwift Generator**

   - Convert JSON workout plans to .zwo files
   - Preview workout structure
   - Export to Zwift folder

4. **📈 Dashboard**
   - Historical trends (TSS, training hours)
   - Power curves
   - Zone distribution

### Method 3: Command Line

```bash
# Run today's automation
python -m src.utils.daily_auto_sync_and_analyze

# Run for specific date
python -m src.utils.daily_auto_sync_and_analyze 2025-11-18

# Sync full week from TrainingPeaks
python -m src.utils.trainingpeaks_sync

# Analyze specific FIT file
python -m src.utils.fit_file_analyzer path/to/workout.fit

# Generate weekly plan
python -m src.utils.ai_coach_engine
```

---

## 🧠 AI Coaching System

### How It Works

The AI coaching system uses a **two-step process** with coaching continuity:

#### Step 1: Weekly Analysis

```python
# Analyzes your past week's training
# Reviews: TSS, workout types, compliance, power trends, HR trends
# AI: Gemini 2.0 Flash Thinking (free, experimental reasoning model)
# Output: Detailed written analysis with insights

Example insights:
- "Strong threshold power improvement evident from recent sessions"
- "Recovery appears adequate based on HR variability"
- "Consider incorporating more Z2 endurance work"
```

#### Step 2: Workout Plan Generation

```python
# Generates next week's training plan
# Context: Last 3 weeks of AI analysis + athlete profile + goals
# AI: Claude Sonnet 4.5 (powerful reasoning for complex planning)
# Output: Structured JSON with 7 days of workouts

Features:
- Progressive overload with proper recovery
- Periodization (base → build → peak → taper)
- Workout variety (intervals, tempo, endurance, recovery)
- Zwift-compatible .zwo file generation
```

### Coaching Continuity Features

**1. Prior AI Analysis Integration**

- System retrieves last 3 weeks of AI coaching analysis
- Claude sees its own previous insights when generating plans
- Creates progressive narrative across weeks
- No "cold start" - each week builds on previous observations

**2. Auto-Updating Coaching Notes**

Just type natural feedback - system extracts structured data:

```
Example feedback:
"Completed my first 100-mile gravel ride this weekend! Felt strong
throughout. My FTP test came in at 310W yesterday. I'm now aiming
for consistent 5-hour endurance rides without bonking."

System auto-detects:
✅ Achievement: "Completed first 100-mile gravel ride"
✅ FTP Update: 300W → 310W
✅ New Goal: "consistent 5-hour endurance rides"
✅ Observation: "Felt strong throughout"
```

**Trigger phrases detected:**

- Achievements: "completed first", "achieved", "new PR", "personal best"
- Goals: "aiming for", "target", "goal is", "working toward"
- FTP: Any 3-digit number near "FTP" (e.g., "310W")
- Phase: "moving into build phase", "starting taper"
- Observations: "feeling", "noticed", "struggling with"

No manual JSON editing required!

---

## 📂 Project Structure

```
fitness_tracker/
├── src/
│   ├── api/                           # FastAPI REST endpoints
│   │   └── app.py
│   ├── models/                        # Data models & schemas
│   │   ├── workout.py
│   │   └── weekly_plan.py
│   ├── storage/                       # Database layer
│   │   └── database.py
│   ├── ui/                            # Streamlit interface
│   │   └── streamlit_app.py
│   └── utils/                         # Core functionality
│       ├── daily_auto_sync_and_analyze.py    # Main automation
│       ├── trainingpeaks_sync.py             # Browser automation
│       ├── fit_file_analyzer.py              # AI workout analysis
│       ├── ai_coach_engine.py                # Weekly planning
│       ├── ai_prompts.py                     # Prompt engineering
│       ├── ai_database_queries.py            # Context retrieval
│       ├── coaching_notes.py                 # Memory system
│       ├── zwift_workout_generator.py        # .zwo file creation
│       ├── dynamic_workout_content.py        # API-based alerts
│       └── rag_loader.py                     # Knowledge base
├── data/
│   ├── fitness_data.db                # SQLite database
│   ├── coaching_notes.json            # AI coach memory
│   ├── ai_coach_output/               # Analysis text files
│   └── rag_context/                   # Knowledge base docs
├── logs/                              # Automation logs
├── tests/                             # Pytest suite
├── archive/                           # Old documentation
├── .env                               # Configuration (gitignored)
├── requirements.txt                   # Python dependencies
├── pytest.ini                         # Test configuration
└── README.md                          # This file
```

---

## 💾 Database Schema

**SQLite database:** `data/fitness_data.db`

### Tables

**1. workouts**

```sql
- workout_day: DATE (PK)
- workout_data: JSON (complete FIT file data)
- created_at: TIMESTAMP
```

**2. personal_bests**

```sql
- effort_type: TEXT (PK: '30s', '1min', ..., '60min')
- power: INTEGER (watts)
- date: DATE
- workout_id: TEXT
```

**3. weekly_summaries**

```sql
- id: INTEGER (PK)
- week_number: INTEGER
- start_date: DATE
- end_date: DATE
- summary_data: JSON
- qualitative_data: JSON
```

**4. weekly_plans**

```sql
- id: INTEGER (PK)
- week_number: INTEGER
- start_date: DATE
- ftp: INTEGER
- workout_data: JSON
- notes: TEXT
```

**5. proposed_workouts**

```sql
- id: INTEGER (PK)
- name: TEXT
- type: TEXT (bike, run, strength, mobility)
- plannedDuration: INTEGER
- sections: JSON
- intervals: JSON
```

---

## 🎨 Workout Plan JSON Format

The system uses structured JSON for workout plans that can be converted to Zwift .zwo files:

```json
{
  "weekNumber": 52,
  "startDate": "2025-12-15",
  "ftp": 300,
  "plannedTSS": {
    "min": 420,
    "max": 460
  },
  "notes": {
    "weekFocus": "Race preparation week",
    "specialConsiderations": "Recovery-focused due to upcoming event"
  },
  "days": [
    {
      "dayNumber": 1,
      "date": "2025-12-15",
      "workouts": [
        {
          "type": "bike",
          "name": "Pre-Race Recovery Spin",
          "plannedDuration": 45,
          "tss": 28,
          "description": "Easy spin to maintain leg turnover",
          "intervals": [
            {
              "name": "Warm-up",
              "duration": 600,
              "powerTarget": {
                "min": 150,
                "max": 170,
                "unit": "watts"
              },
              "cadence": "85-95 rpm"
            },
            {
              "name": "Easy Spin",
              "duration": 1800,
              "powerTarget": {
                "value": 55,
                "unit": "ftp_percent"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

**Supported workout types:**

- `bike`: Cycling workouts (intervals, tempo, endurance, recovery)
- `run`: Running workouts
- `strength`: Resistance training (sets, reps, tempo)
- `mobility`: Yoga, stretching, foam rolling (duration, perSide)

---

## 💰 Cost Breakdown

### Option 1: Free Tier (Analysis Only)

- **Gemini 2.0 Flash**: Free up to 10 requests/min
- **Analysis**: ~0.0003 per workout
- **Monthly cost**: $0.00 (free tier sufficient for 1-2 workouts/day)

### Option 2: Full AI Coaching (~$2/month)

- **Gemini 2.0 Flash Thinking**: Free (experimental model)
- **Claude Haiku**: $0.008 per analysis
- **Claude Sonnet 4.5**: $0.156 per plan generation
- **Weekly**: $0.164
- **Monthly**: $0.656 (~$0.66)
- **With daily analysis**: ~$2/month total

### Option 3: Original Implementation (deprecated)

- **GPT-4**: $0.50-1.00 per analysis
- **Monthly**: $60-90
- **Savings**: 95%+ with current approach

**Optimization strategies implemented:**

- Free Gemini models for daily analysis
- Haiku for simple tasks (cheap)
- Sonnet only for complex planning (selective)
- Dynamic model discovery (auto-updates as new free models release)
- Batch processing to minimize API calls

---

## 🔐 Privacy & Security

### Personal Data Handling

**Data stored locally:**

- All workout data in SQLite database
- Coaching notes in JSON file
- FIT files temporarily downloaded
- Analysis text files

**Gitignored files:**

```
.env                    # API keys & credentials
data/fitness_data.db    # Your workout data
data/coaching_notes.json  # Your goals & milestones
logs/                   # Automation logs
*.fit                   # FIT files
```

**Preparing for GitHub push:**

1. Remove personal details from `coaching_notes.json`
2. Clear `data/fitness_data.db` (or don't commit)
3. Clear `logs/` directory
4. Verify `.env` is gitignored
5. Update example configs with placeholders

**API data transmission:**

- Workout data sent to Gemini/Claude for analysis
- Anonymized (no names unless in coaching notes)
- Not stored by API providers beyond session
- Use environment variables for credentials

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_fit_parser_and_athlete_settings.py

# Run with coverage
pytest --cov=src tests/

# Run tests in verbose mode
pytest -v
```

**Test coverage includes:**

- FIT file parsing
- Database operations
- AI prompt engineering
- Workout JSON validation
- Zwift .zwo generation
- Coaching notes auto-update

---

## 🚧 Troubleshooting

### TrainingPeaks Sync Issues

**Problem:** "Login failed" or "Timeout"

```bash
# Check credentials
cat .env | grep TRAININGPEAKS

# Run sync manually to see errors
python -m src.utils.trainingpeaks_sync

# Check browser logs
DEBUG=1 python -m src.utils.trainingpeaks_sync
```

**Problem:** "No workouts found"

- TrainingPeaks may not have FIT file for that day
- Check if workout was manually entered vs uploaded
- Try syncing a different date

### AI Analysis Issues

**Problem:** "Gemini API key invalid"

```bash
# Verify key in .env
echo $GEMINI_API_KEY

# Test API directly
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print(genai.list_models())"
```

**Problem:** "Rate limit exceeded"

- Free tier: 10 requests/min
- Solution: Add delays between requests
- Or upgrade to paid tier

### Database Issues

**Problem:** "Database locked"

```bash
# Check for other processes
lsof data/fitness_data.db

# Close all connections and retry
```

**Problem:** "Table doesn't exist"

```bash
# Re-initialize database
python -c "from src.storage.database import WorkoutDatabase; db = WorkoutDatabase(); print('Database initialized')"
```

### Zwift File Issues

**Problem:** ".zwo file not appearing in Zwift"

- Check Zwift workouts directory path in `.env`
- Default: `~/Documents/Zwift/Workouts/<ZWIFT_ID>/`
- Restart Zwift after adding new files

**Problem:** "Workout displays incorrectly"

- Validate JSON structure
- Check interval durations (must be in seconds)
- Verify power targets (watts or FTP%)

---

## 📚 Additional Documentation

Detailed guides available in project:

- **`COACHING_CONTINUITY_QUICK_REFERENCE.md`**: User guide for AI coaching features
- **`AI_COACHING_CONTINUITY.md`**: Technical details on memory system
- **`AUTOMATION_GUIDE.md`**: Setup instructions for cron automation
- **`DAILY_AUTOMATION_DATA_FLOW.md`**: System architecture diagrams

Archived documentation in `archive/old_docs/`:

- Previous implementation approaches
- Migration guides
- Legacy prompt engineering docs

---

## 🛠️ Development

### Adding New Features

**1. New API Endpoint:**

```python
# src/api/app.py
@app.get("/api/new-feature")
async def new_feature():
    return {"status": "success"}
```

**2. New Database Table:**

```python
# src/storage/database.py
def create_new_table(self):
    self.conn.execute("""
        CREATE TABLE IF NOT EXISTS new_table (
            id INTEGER PRIMARY KEY,
            data TEXT
        )
    """)
```

**3. New Workout Type:**

```python
# src/utils/ai_coach_engine.py
# Add to WORKOUT_TYPES constant
# Update JSON schema validation
# Add Zwift .zwo generation logic
```

### Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

**Coding standards:**

- Python 3.10+ type hints
- Docstrings for all functions
- Pytest for new features
- Follow existing code style

---

## 📈 Roadmap

### In Progress

- 🧠 **Week Number Extraction**: Better parsing of "Week X" from analysis
- 🏆 **Achievement Categories**: Classify milestones (distance, power, endurance)
- 🎯 **Goal Prioritization**: Rank goals by recency and specificity
- 💭 **Sentiment Analysis**: Detect athlete mood/motivation from feedback
- 🔄 **Recurring Schedule Learning**: Auto-detect patterns (e.g., "Tuesday races")

### Planned

- 📊 **Multi-Week Pattern Recognition**: Identify trends across 4+ weeks
- 🎨 **Adaptive Prompting**: Adjust AI prompts based on coaching continuity
- ⭐ **Feedback Quality Scoring**: Encourage athletes to provide rich input
- 📈 **Milestone Visualization**: Timeline UI for achievements
- 📱 **Mobile App**: React Native companion app
- 🌐 **Web Dashboard**: Public progress sharing (optional)

### Future Ideas

- Integration with Garmin Connect
- Integration with Strava
- Real-time workout analysis (live FIT parsing)
- Social features (compare with friends)
- Nutrition tracking integration
- Sleep quality correlation

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

**APIs Used:**

- **Gemini** (Google): Free AI for workout analysis
- **Claude** (Anthropic): AI for workout planning
- **Quotable API**: Inspirational quotes
- **JokeAPI**: Dad jokes and trivia
- **Numbers API**: Fun number facts
- **AdviceSlip**: Random advice
- **Affirmations API**: Positive affirmations
- **HackerNews**: Tech/science news
- **arXiv**: Research papers
- **Wikipedia**: On this day in history

**Libraries:**

- **Streamlit**: Beautiful web UI
- **Playwright**: Browser automation
- **fitparse**: FIT file parsing
- **anthropic**: Claude API
- **google-generativeai**: Gemini API

---

## 📧 Contact

For questions, issues, or feature requests:

- GitHub Issues: [Open an issue](https://github.com/yourusername/fitness_tracker/issues)
- Email: your.email@example.com

---

**Built with ❤️ for endurance athletes who love data**

_Last Updated: December 14, 2025_
