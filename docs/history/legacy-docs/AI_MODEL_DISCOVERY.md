# Dynamic AI Model Discovery

## Overview

The fitness tracker now automatically discovers and uses available free Google Gemini models, making it resilient to model changes and quota limits.

## How It Works

### 1. Automatic Model Discovery

- Queries Google's API for all available Gemini models
- Filters for free-tier models (flash, pro variants)
- Prioritizes by stability and speed
- Caches results for 24 hours

### 2. Smart Fallback System

```
Try Model 1 (e.g., gemini-2.0-flash-lite-001)
  ↓ Quota exceeded?
Try Model 2 (e.g., gemini-2.0-flash-001)
  ↓ Not available?
Try Model 3 (e.g., gemini-1.5-flash-002)
  ↓ Success!
Use this model ✅
```

### 3. Cost Optimization

**High Volume (Daily Analysis):**

- Uses dynamic free model discovery
- Cycles through 7+ free models automatically
- Prioritizes fastest models (flash variants)
- **Cost: $0** 💰

**Low Volume (Weekly Planning):**

- Uses premium models (Claude Sonnet 4.5)
- Better reasoning for strategic planning
- Only 1-2 calls per week
- **Cost: ~$0.50/week** 💰

## Usage

### In Code

```python
from src.utils.fit_file_analyzer import FitFileAnalyzer

# Enable dynamic discovery (default)
analyzer = FitFileAnalyzer(use_dynamic_models=True)

# Or use static fallback
analyzer = FitFileAnalyzer(use_dynamic_models=False)
```

### In Streamlit

1. Navigate to **📥 Sync & Analyze Workouts** tab
2. Expand **🤖 AI Model Management (Advanced)**
3. Click **🔄 Refresh Available Models**

This will:

- Query Google's API for current models
- Test which models are working
- Cache results for faster future use
- Show you the best available model

### Command Line

```bash
# Refresh model cache
python refresh_gemini_models.py

# Test discovery system
python -m src.utils.gemini_model_discovery
```

## Model Prioritization

Models are scored based on:

1. **Type** (100 points)

   - Flash models: +100 (fastest, free)
   - Pro models: +50 (more capable)

2. **Stability** (50 points)

   - Stable: +50
   - Experimental: +10

3. **Version** (30 points)

   - `-002`: +30 (latest stable)
   - `-001`: +20
   - No version: +0

4. **Generation** (40 points)

   - 2.0: +40 (newest)
   - 1.5: +30
   - 1.0: +10

5. **Size** (25 points)
   - `8b` (lightweight): +25

**Example Scores:**

- `gemini-2.0-flash-lite-001`: 195 points ⭐
- `gemini-1.5-flash-002`: 180 points
- `gemini-1.5-pro`: 130 points
- `gemini-pro`: 50 points

## Cache System

**Location:** `data/gemini_models_cache.json`

**Contents:**

```json
{
  "timestamp": "2025-12-07T10:30:00",
  "models": [
    "gemini-2.0-flash-lite-001",
    "gemini-2.0-flash-001",
    ...
  ]
}
```

**Refresh Interval:** 24 hours

**Benefits:**

- Reduces API calls (1 call per day vs. per workout)
- Faster startup (no discovery delay)
- Works offline (uses cached list)

## When to Refresh

### Automatically

- Cache expires after 24 hours
- Next workout analysis will refresh

### Manually

**Refresh if:**

- ❌ Getting "no available models" errors
- 📊 Quota exhausted on all models
- 🆕 Google released new models (check [Google AI Studio](https://aistudio.google.com))
- 📅 Haven't refreshed in >1 week

**How to Refresh:**

1. Streamlit UI: Click **🔄 Refresh Available Models**
2. Command line: `python refresh_gemini_models.py`
3. Delete cache: `rm data/gemini_models_cache.json`

## Troubleshooting

### "No available models" Error

**Cause:** All free models exhausted quota limits

**Solutions:**

1. Wait 24 hours for quota reset
2. Refresh model list (new models may be available)
3. Check [Google AI Studio](https://aistudio.google.com) for your quota status

### Discovery Fails

**Fallback Behavior:**

- Uses static hardcoded list
- Still tries 7 models
- No functionality lost

**Fix:**

1. Check `GEMINI_API_KEY` in `.env`
2. Verify API key is valid
3. Check internet connection

### Slow First Run

**Normal:** First run queries Google's API (~5 seconds)

**After First Run:** Uses cache (instant)

## Files

```
src/utils/
├── gemini_model_discovery.py  # Core discovery logic
├── fit_file_analyzer.py        # Uses dynamic models
└── ai_coach_engine.py          # Uses premium models

data/
└── gemini_models_cache.json    # 24hr cache

refresh_gemini_models.py         # CLI refresh tool
```

## Cost Comparison

### Without Dynamic Discovery

- Fixed model list
- Breaks when Google removes models
- Manual updates required
- **Risk:** Analysis stops working

### With Dynamic Discovery

- Always uses latest free models
- Self-healing on quota limits
- Zero maintenance
- **Risk:** None - automatic fallback

## Future Improvements

- [ ] Add support for other free AI providers (Anthropic, OpenAI)
- [ ] Implement circuit breaker pattern for failed models
- [ ] Track model performance metrics
- [ ] Auto-switch to faster models when available
- [ ] Quota tracking per model

## API Reference

See `src/utils/gemini_model_discovery.py` for full API documentation.

**Key Classes:**

- `GeminiModelDiscovery`: Main discovery engine
- `get_best_free_models()`: Quick function to get top models
