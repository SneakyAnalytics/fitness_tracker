# AI Model Architecture - Cost Optimization

## Complete System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FITNESS TRACKER AI SYSTEM                        │
│                                                                     │
│  ┌────────────────────────────┐  ┌────────────────────────────┐   │
│  │   HIGH VOLUME OPERATIONS   │  │   LOW VOLUME OPERATIONS    │   │
│  │     (FREE MODELS)          │  │    (PREMIUM MODELS)        │   │
│  └────────────────────────────┘  └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
         │                                      │
         │                                      │
         ▼                                      ▼
┌─────────────────────┐              ┌──────────────────────┐
│  Dynamic Discovery  │              │  Claude Sonnet 4.5   │
│  Gemini Models      │              │  (Strategic Only)    │
│                     │              │                      │
│  • Flash-lite-001   │              │  • Weekly Planning   │
│  • Flash-001        │              │  • Race Analysis     │
│  • Flash-lite-002   │              │  • Training Strategy │
│  • ...28 models     │              │                      │
│                     │              │  Cost: $0.50/week    │
│  Cost: $0/analysis  │              │  ($2/month)          │
└─────────────────────┘              └──────────────────────┘
         │                                      │
         │                                      │
         ├──────────────────┬───────────────────┤
         │                  │                   │
         ▼                  ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Daily Automation│  │ Batch Sync      │  │ Weekly Review   │
│                 │  │ (Date Range)    │  │ & Plan Gen      │
│ • Auto-sync     │  │                 │  │                 │
│ • Auto-analyze  │  │ • 5-30 workouts │  │ • 1x per week   │
│ • Every night   │  │ • User-triggered│  │ • Deep analysis │
│                 │  │ • Any date range│  │ • Next week plan│
│ Cost: $0/day    │  │                 │  │                 │
│                 │  │ Cost: $0/batch  │  │ Cost: $0.50     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                  │                   │
         ▼                  ▼                   ▼
┌──────────────────────────────────────────────────────────┐
│              FITNESS_DATA.DB (SQLite)                    │
│                                                          │
│  • workout_analyses (AI insights)                       │
│  • proposed_workouts (training plans)                   │
│  • weekly_summaries (performance tracking)              │
│  • athlete_settings (FTP, zones, goals)                 │
└──────────────────────────────────────────────────────────┘


## Model Selection Logic

┌─────────────────────────────────────────────────────────────────┐
│  FitFileAnalyzer(use_dynamic_models=True)                       │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  Check Cache (24hr)    │
              └────────────────────────┘
                          │
                ┌─────────┴─────────┐
                │                   │
         Cache Hit              Cache Miss
                │                   │
                ▼                   ▼
    ┌────────────────────┐  ┌──────────────────┐
    │  Use Cached Models │  │ Query Google API │
    │  (28 free models)  │  │ genai.list_models│
    └────────────────────┘  └──────────────────┘
                │                   │
                │            ┌──────┴──────┐
                │            │             │
                │        Success      API Fails
                │            │             │
                │            ▼             ▼
                │    ┌──────────────┐  ┌─────────────┐
                │    │ Score Models │  │   Fallback  │
                │    │ Save Cache   │  │ Static List │
                │    └──────────────┘  └─────────────┘
                │            │             │
                └────────────┴─────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ Try Model #1                 │
              │ gemini-2.0-flash-lite-001    │
              └──────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                Success           Fails
                    │                 │
                    ▼                 ▼
            ┌──────────────┐  ┌──────────────┐
            │   Complete   │  │ Try Model #2 │
            │  Analysis    │  │ (auto-retry) │
            └──────────────┘  └──────────────┘
                                      │
                             (Up to 7 retries)
                                      │
                                      ▼
                            ┌──────────────────┐
                            │ Eventually Works │
                            │ or Shows Error   │
                            └──────────────────┘


## Cost Comparison

┌──────────────────────────────────────────────────────────────┐
│                    BEFORE OPTIMIZATION                       │
│                                                              │
│  Daily Automation:     30 days × $1.50 = $45/month         │
│  Batch Analysis:       4 batches × $3.75 = $15/month       │
│  Single Uploads:       10 uploads × $0.50 = $5/month       │
│  Weekly Planning:      4 weeks × $0.50 = $2/month          │
│                                                              │
│  TOTAL: $67/month ($804/year)                               │
└──────────────────────────────────────────────────────────────┘

                            ⬇️  OPTIMIZATION  ⬇️

┌──────────────────────────────────────────────────────────────┐
│                     AFTER OPTIMIZATION                       │
│                                                              │
│  Daily Automation:     30 days × $0 = $0/month  ✅         │
│  Batch Analysis:       4 batches × $0 = $0/month  ✅       │
│  Single Uploads:       10 uploads × $0 = $0/month  ✅      │
│  Weekly Planning:      4 weeks × $0.50 = $2/month  ⭐      │
│                                                              │
│  TOTAL: $2/month ($24/year)                                 │
│                                                              │
│  SAVINGS: $65/month ($780/year)  🎉                         │
└──────────────────────────────────────────────────────────────┘


## Cache System

┌────────────────────────────────────────────────────────────┐
│  data/gemini_models_cache.json                             │
│                                                            │
│  {                                                         │
│    "models": [                                             │
│      "gemini-2.0-flash-lite-001",                         │
│      "gemini-2.0-flash-001",                              │
│      ...28 models                                          │
│    ],                                                      │
│    "timestamp": "2025-01-XX 10:30:00",                    │
│    "expiry": "2025-01-XX 10:30:00"  (24hr)                │
│  }                                                         │
│                                                            │
│  Refresh: Automatic (every 24hr) or Manual                │
│  Command: python refresh_gemini_models.py                 │
└────────────────────────────────────────────────────────────┘


## UI Locations

┌──────────────────────────────────────────────────────────────┐
│                    STREAMLIT APP TABS                        │
│                                                              │
│  📥 Sync & Analyze Workouts                                 │
│     ├─ Upload FIT File (FREE ✅)                            │
│     └─ 🤖 AI Model Management                               │
│                                                              │
│  🔄 Historical Analysis                                      │
│     └─ 🔄 Batch Sync & Analyze (Date Range) (FREE ✅)       │
│                                                              │
│  📊 AI Weekly Planning & Analysis                            │
│     └─ Generate Weekly Plan (PREMIUM ⭐ $0.50)             │
│                                                              │
│  📈 Training Dashboard                                       │
│     └─ View analyzed workouts (FREE)                        │
└──────────────────────────────────────────────────────────────┘
```
