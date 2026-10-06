# Issues Resolved - January 22, 2026

## Issue 1: News Source Imbalance ✅ FIXED

### Problem

User reported that workouts only contained news from two sources:

- The Oregonian
- MLB RSS feeds

Expected behavior was a diverse mixture from all 23 configured news sources.

### Root Cause

The `_get_team_news_story()` method in `dynamic_workout_content.py` was iterating through news sources **sequentially** rather than randomly. This meant:

- High-volume feeds (Oregonian, MLB News) with frequent updates would always be checked first
- They would return stories more often than beat writer feeds with sporadic updates
- Sequential iteration created a bias toward sources earlier in the list

### Solution Implemented

Modified `_get_team_news_story()` to randomize source order before iteration:

```python
# Before:
for source in self.team_news_sources:
    # Check source for stories...

# After:
sources = list(self.team_news_sources)
random.shuffle(sources)  # Randomize order for diversity
for source in sources:
    # Check source for stories...
```

### Testing & Validation

Created test script (`test_news_diversity.py`) that fetches 20 stories and measures source distribution:

**Results:**

- **10 unique sources** used across 20 fetches (out of 23 configured)
- No single source dominated (max 3 appearances each)
- Sources included: Mets writers, Ducks writers, Chiefs writers, Oregonian, MLB News, AI Tech News
- ✅ **Good diversity achieved**

### Files Modified

- `/Users/jacobrobinson/fitness_tracker/src/utils/dynamic_workout_content.py` (lines 782-822)
- Copied to Beelink and API container restarted to apply changes

---

## Issue 2: Beelink Fan Running Constantly ✅ FIXED

### Problem

User noticed the Beelink's fan running non-stop since January 21, indicating high resource usage.

### Root Cause

The `vmmemWSL` process (Windows Subsystem for Linux memory management used by Docker Desktop) had accumulated:

- **242,945 CPU seconds** (~67 hours of CPU time)
- **1+ GB of memory**

This was likely caused by extended Docker container runtime without WSL being restarted.

### Solution Implemented

Executed `wsl --shutdown` to gracefully terminate WSL, which:

- Releases accumulated memory
- Resets WSL VM state
- Allows Docker to restart WSL cleanly when containers restart

### Results

**Before Shutdown:**

```
ProcessName        CPU (seconds)  Memory (MB)
vmmemWSL           242,945        1,037
```

**After Shutdown:**

```
ProcessName        CPU (seconds)  Memory (MB)
vmmemWSL           92.52          2,122
```

**Docker Container Health:**

- fitness-tracker-api: 6-9% CPU, ~95-117 MB RAM
- fitness-tracker-ui: 0% CPU, ~72-77 MB RAM
- Both containers running normally with minimal resource usage

### Recommendation

If fan issues recur, consider:

1. Periodic WSL restarts (e.g., weekly): `wsl --shutdown`
2. Configuring WSL2 memory limits in `.wslconfig` file
3. Monitoring Docker container logs for any runaway processes

---

## Configured News Sources (23 Total)

### Mets Coverage (3 beat writers + 1 official)

- Anthony DiComo
- Tim Britton
- Abbey Mastracco
- Official MLB News

### Oregon Ducks Football (6 beat writers + 1 official)

- James Crepea
- Alec Dietz
- Zachary Neel
- Aaron Fentress
- Ryan Clarke
- Bill Oram
- Official Oregon Ducks Football

### Portland Timbers (4 beat writers + 2 official)

- Ryan Clarke
- Matt Pentz
- Judah Newby
- Jake Zivin
- Official MLS News
- Official Portland Timbers

### Kansas City Chiefs (3 beat writers + 1 official)

- Nate Taylor
- Jesse Newell
- Matt Derrick
- Official NFL News

### Other

- The Oregonian (local news)
- AI Tech News

All sources are RSS feeds from Google News searches (for beat writers) or official league/team feeds.

---

## Next Steps

1. **Monitor news diversity** in tomorrow's workouts (Jan 23) to confirm fix is working in production
2. **Watch Beelink fan behavior** over next few days to ensure performance issue is resolved
3. **Consider implementing source usage tracking** to enforce minimum usage of each source over time
4. **Optional: Add logging** to track which sources are most reliable for fresh content

---

## Files Changed

- `src/utils/dynamic_workout_content.py` - Added source randomization
- `test_news_diversity.py` - New test script for validation

## Commands Executed

```bash
# Fix deployment
scp src/utils/dynamic_workout_content.py rakej@100.117.194.8:C:/Users/rakej/fitness_tracker/src/utils/
docker restart fitness-tracker-api

# WSL memory fix
wsl --shutdown

# Testing
docker cp test_news_diversity.py fitness-tracker-api:/app/
docker exec fitness-tracker-api python /app/test_news_diversity.py
```
