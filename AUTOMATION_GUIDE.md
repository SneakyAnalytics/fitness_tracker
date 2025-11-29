# Automated Daily TrainingPeaks Sync & Analysis

## 🎯 Overview

Complete end-to-end automation that runs at 10pm PST every day:

1. **🔐 TrainingPeaks Login** - Headless browser automation
2. **📥 Download Workouts** - Today's FIT files, workout summaries, metrics
3. **💾 Database Storage** - Automatic upload via API
4. **🤖 AI Analysis** - Gemini-powered workout insights
5. **🏅 Personal Best Tracking** - Top 3 efforts across 7 durations
6. **🧹 Automatic Cleanup** - Removes temporary files

**No manual file management. No downloads folder clutter. Completely hands-off.**

## 🚀 Quick Setup

### 1. Run Setup Script

```bash
./setup_daily_automation.sh
```

This will:

- Test the automation module
- Show cron job configuration
- Create logs directory
- Display manual run options

### 2. Configure Cron Job

```bash
# Edit crontab
crontab -e

# Add this line:
0 22 * * * cd /Users/jacobrobinson/fitness_tracker && /Users/jacobrobinson/fitness_tracker/venv/bin/python -m src.utils.daily_auto_sync_and_analyze >> /Users/jacobrobinson/fitness_tracker/logs/daily_automation.log 2>&1
```

### 3. Verify Setup

```bash
# Check crontab
crontab -l

# Test manual run
python -m src.utils.daily_auto_sync_and_analyze
```

## 📋 How It Works

### Complete Workflow

```
10:00 PM PST
    ↓
[1] Launch headless Chrome browser
    ↓
[2] Navigate to TrainingPeaks.com
    ↓
[3] Login with your credentials
    ↓
[4] Navigate to export page
    ↓
[5] Set date range to today only
    ↓
[6] Download 3 export files:
    - WorkoutFileExport-*.zip (FIT files)
    - WorkoutExport-*.zip (workout summary CSV)
    - MetricsExport-*.zip (daily metrics CSV)
    ↓
[7] Extract FIT files from ZIP
    ↓
[8] Upload each FIT file to API/database
    ↓
[9] Upload CSV files to API/database
    ↓
[10] For each workout:
     - Parse FIT file
     - Detect peak efforts (7 durations)
     - Send to Gemini AI for analysis
     - Compare to personal bests
     - Store analysis + PBs in database
     - Wait 6 seconds (rate limiting)
    ↓
[11] Clean up all temporary files:
     - Delete FIT files
     - Delete ZIP files
     - Remove empty directories
    ↓
[12] Log summary to logs/daily_automation.log
    ↓
Done! 🎉
```

### What Gets Cleaned Up

**Automatically removed after processing:**

- `~/Downloads/WorkoutFileExport-*.zip`
- `~/Downloads/WorkoutExport-*.zip`
- `~/Downloads/MetricsExport-*.zip`
- `~/Downloads/trainingpeaks_extracted/*.fit`
- Empty subdirectories

**Your downloads folder stays clean!**

## 💻 Usage Options

### Option 1: Automated (Recommended)

Set up cron job (see above) and forget about it. Runs every night at 10pm PST.

### Option 2: Manual (Streamlit UI)

```bash
# Start Streamlit
streamlit run src/ui/streamlit_app.py

# Navigate to:
Performance Analytics → Auto Analysis → "Run Complete Automation Now"
```

### Option 3: Manual (Command Line)

```bash
# Run for today
python -m src.utils.daily_auto_sync_and_analyze

# Run for specific date
python -m src.utils.daily_auto_sync_and_analyze 2025-11-17
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Required
TRAININGPEAKS_USERNAME=your_email@example.com
TRAININGPEAKS_PASSWORD=your_password
GEMINI_API_KEY=your_gemini_key

# Optional
ANTHROPIC_API_KEY=your_claude_key  # For workout generation
```

### FTP Setting

Default: 330W

Change in:

- Streamlit UI when running manually
- Code: `daily_auto_sync_and_analyze.py` line 350

## 📊 What Gets Analyzed

### FIT File Data

- Duration, distance, elevation
- Power: average, normalized, max
- Heart rate: average, max
- Cadence, speed
- TSS (Training Stress Score)

### Peak Efforts (7 Durations)

- 30 seconds (sprint power)
- 1 minute (VO2max)
- 3 minutes (VO2max sustained)
- 5 minutes (threshold+)
- 10 minutes (threshold)
- 20 minutes (FTP test)
- 60 minutes (endurance)

### AI Insights

- **Workout Quality**: Rating and assessment
- **Effort Distribution**: Zone analysis
- **Recovery Needs**: Rest recommendations
- **Training Suggestions**: What to focus on next

### Personal Bests

- Top 3 efforts for each duration
- Medal rankings: 🥇 Gold, 🥈 Silver, 🥉 Bronze
- Achievement dates
- Historical comparison

## 📈 Viewing Results

### Streamlit UI

1. **Performance Analytics** page
2. **Personal Bests** tab → Medal podium view
3. **Manual Upload** tab → View specific analysis
4. **Historical Data** tab → Trends over time

### Database

All data stored in `data/fitness_data.db`:

- `workout_analyses` table
- `personal_bests` table
- Complete FIT file metrics

## 🍎 Mac Closed Lid Options

### Problem

Macs (especially Apple Silicon) may not run cron jobs when the lid is closed.

### Solutions

**Option 1: Keep Laptop Docked/Open** (Simplest)

- Use external monitor
- Laptop stays awake when plugged in
- Cron jobs run normally

**Option 2: Disable Sleep When Plugged In**

```bash
# System Settings approach
System Settings → Lock Screen → Turn display off: Never (when plugged in)

# Command line approach
sudo pmset -c sleep 0
sudo pmset -c disksleep 0
```

**Option 3: Enable Power Nap** (If Supported)

```bash
System Settings → Battery → Options → Enable Power Nap while plugged into power
```

**Option 4: Use Cloud/Server**

- Run on AWS, DigitalOcean, etc.
- More reliable for scheduled tasks
- No laptop power concerns

**Option 5: GitHub Actions** (Advanced)

- Set up workflow to run at 10pm
- Triggers automation remotely
- Free for public repos

## 🐛 Troubleshooting

### No Workouts Downloaded

**Symptoms:**

- "No FIT files found after sync"
- Browser automation fails

**Solutions:**

1. Check TrainingPeaks credentials in `.env`
2. Verify you have workouts for target date
3. Run manual test to see browser automation
4. Check if CAPTCHA is blocking login
5. Look at logs: `tail -f logs/daily_automation.log`

### Analysis Fails

**Symptoms:**

- "Failed to analyze workout"
- Gemini API errors

**Solutions:**

1. Verify `GEMINI_API_KEY` in `.env`
2. Check API rate limits (10/min free tier)
3. Review error in logs
4. Test individual FIT file manually

### Files Not Cleaned Up

**Symptoms:**

- Temporary files remain in downloads

**Solutions:**

1. Check automation completed successfully
2. Verify file permissions
3. Run cleanup manually:
   ```python
   from src.utils.daily_auto_sync_and_analyze import DailyAutoSyncAndAnalyze
   automation = DailyAutoSyncAndAnalyze()
   automation.cleanup_temp_files()
   ```

### Cron Not Running

**Symptoms:**

- No log entries at 10pm
- Automation never runs

**Solutions:**

1. Verify cron is running: `ps aux | grep cron`
2. Check crontab: `crontab -l`
3. Test with earlier time to verify
4. Check system logs: `log show --predicate 'process == "cron"' --last 1h`
5. Ensure Full Disk Access for cron (Mac):
   - System Settings → Privacy & Security → Full Disk Access
   - Add `/usr/sbin/cron`

## 📊 Logs & Monitoring

### Log Location

```
/Users/jacobrobinson/fitness_tracker/logs/daily_automation.log
```

### View Live Logs

```bash
tail -f logs/daily_automation.log
```

### Check Recent Runs

```bash
tail -100 logs/daily_automation.log
```

### Example Log Output

```
2025-11-18 22:00:01 - INFO - ============================================================
2025-11-18 22:00:01 - INFO - 🚀 DAILY AUTOMATION - 2025-11-18
2025-11-18 22:00:01 - INFO - ============================================================
2025-11-18 22:00:01 - INFO - STEP 1: TrainingPeaks Sync
2025-11-18 22:00:15 - INFO - ✅ TrainingPeaks sync completed
2025-11-18 22:00:15 - INFO -    FIT files uploaded: 1
2025-11-18 22:00:15 - INFO - STEP 2: Find FIT Files
2025-11-18 22:00:15 - INFO - Found 1 FIT file(s) for 2025-11-18
2025-11-18 22:00:15 - INFO - STEP 3: AI Analysis
2025-11-18 22:00:16 - INFO - [1/1] 2025-11-18-Threshold-Intervals.fit
2025-11-18 22:00:20 - INFO -    ✅ Analysis complete
2025-11-18 22:00:20 - INFO -    💾 Stored analysis ID: 45
2025-11-18 22:00:20 - INFO -    🏅 New PB: 5min = 310.5W
2025-11-18 22:00:20 - INFO - STEP 4: Cleanup
2025-11-18 22:00:20 - INFO - 🧹 Cleaning up temporary files...
2025-11-18 22:00:20 - INFO -    🗑️  Removed: 2025-11-18-Threshold-Intervals.fit
2025-11-18 22:00:20 - INFO - ✅ Cleanup complete
2025-11-18 22:00:20 - INFO - ============================================================
2025-11-18 22:00:20 - INFO - ✅ DAILY AUTOMATION COMPLETE
2025-11-18 22:00:20 - INFO - FIT Files Downloaded: 1
2025-11-18 22:00:20 - INFO - Workouts Analyzed: 1
2025-11-18 22:00:20 - INFO - New Personal Bests: 1
```

## 🎯 API Rate Limits

### Gemini Free Tier

- **Rate**: 10 requests/minute
- **Daily**: 1,500 requests/day
- **Solution**: 6-second delay between analyses

### Cost Estimate

- **Gemini Analysis**: ~$0.0001-0.0003 per workout
- **Daily**: 1-3 workouts = $0.0003-0.0009
- **Weekly**: ~$0.002-0.006
- **Monthly**: ~$0.01-0.03

**Extremely affordable for daily automation!**

## 🔒 Security Notes

### Credentials Storage

- Stored in `.env` file (git-ignored)
- Never committed to version control
- Browser automation uses secure session

### TrainingPeaks Access

- Headless browser runs locally
- No credentials sent to third parties
- Session closes after download

### API Keys

- Gemini: Used only for AI analysis
- Claude: Used only for workout generation (optional)
- Both encrypted in transit

## 🎉 Benefits Summary

✅ **Fully Automated** - Set it and forget it  
✅ **No Manual Work** - Everything happens automatically  
✅ **Clean Downloads** - Temp files removed after processing  
✅ **AI Insights** - Gemini analysis for every workout  
✅ **Personal Bests** - Automatic tracking with medals  
✅ **Rate Limit Safe** - Built-in delays respect API limits  
✅ **Cost Effective** - ~$0.02/week for complete automation  
✅ **Comprehensive Logs** - Full visibility into every run

---

**Questions?** Check the troubleshooting section or view logs: `tail -f logs/daily_automation.log`

**Happy Training! 🚴‍♂️🎯**
