# Agent Learnings & Debugging Notes

A running record of bugs found, root causes, and fixes applied — so the same mistakes aren't repeated.

---

## 2026-04-26 — AI Coach plan saved to wrong week / wrong dates

### Symptom

Generating a new plan via the AI Coach saved the plan with **week 52** and dates in **November 2025** (~22 weeks in the past), even though we were in week 75-76 of April 2026.

### Root Cause

`generate_plan()` in `src/utils/ai_chat_session.py` passed a `user_context` dict to the prompt builder that **never included `next_week_number` or `next_week_start_date`**.  
The prompt template in `src/utils/ai_prompts.py` fell back to hardcoded defaults:

```python
week_number = (context.user_context or {}).get('next_week_number', 52)          # ← default 52
start_date  = (context.user_context or {}).get('next_week_start_date', '2025-11-18')  # ← stale date
```

These defaults were set during initial development and never updated or made dynamic.

### Fix Applied

In `generate_plan()`, before building `user_context`, we now:

1. Compute `next_week_start_date` = `self.week_start_date` + 7 days (the Monday of the upcoming plan week).
2. Query the DB for `MAX(weekNumber)` from `weekly_plans` and set `next_week_number = max + 1` (or reuse if an entry already exists for that start date).
3. Inject both values into `user_context` so the prompt template receives the correct numbers.

```python
next_week_start_date = (datetime.strptime(self.week_start_date, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
# ... db query for max week ...
user_context = {
    "week_feedback": conversation_summary,
    "context_type": "upcoming_week",
    "next_week_number": next_week_number,
    "next_week_start_date": next_week_start_date,
}
```

### Data Fix

The one bad plan (week 76, stored with 2025-11-18 dates) was corrected in the live DB via `fix_week76_dates.py`:

- `daily_plans.date` for days 1–7 → `2026-04-27` .. `2026-05-03`
- `weekly_plans.startDate` → `2026-04-27`
- `coach_chat_sessions.current_plan` JSON → `weekNumber: 76`, `startDate: 2026-04-27`, all day dates corrected

### Lesson

**Never use hardcoded date/week defaults in prompt templates.** Defaults that made sense at initial development become invisible bugs months later. The call site (`generate_plan`) must always populate these values dynamically from the DB before invoking the prompt builder.

---

## 2026-04-26 — AI Coach plan generation JSON truncation & token limits

### Symptom

Generated plans were cut off mid-JSON; the save would fail silently or produce a partial 3-4 day plan.

### Root Cause

`max_tokens` was set to 8000, insufficient for a full 7-day plan with detailed intervals. The JSON parser also relied on a simple regex that failed on multi-level nesting when the response was truncated.

### Fix Applied

- Raised `max_tokens` to `16000` in `_call_api_streaming`.
- Replaced the JSON extraction with a `raw_decode` approach that walks the response and extracts the largest valid JSON object.
- Added `_extract_partial_plan()` to structurally reconstruct day objects even from a truncated stream.
- Added a continuation prompt that requests missing days when the initial response only returns some of the 7 days.
- Phase now resets to `CLARIFYING` (not stuck in `GENERATING`) on failure so the user can retry.

---

## Deployment Notes (Beelink)

- Beelink is **Windows** (`C:/Users/rakej/...`) with **no rsync or git** — only `tar`, `scp`, Docker Compose.
- Deploy: push to `main` → GitHub Actions tests and publishes images to ghcr.io →
  `./deploy_to_beelink.sh` pulls them (backs up the DB first, health-checks after).
  Full procedure, rollback and Windows/WSL stability notes: `docs/deployment/RUNBOOK.md`.
- Containers run code **from the image only**. Do NOT go back to copying `.py` files into the `fitness_tracker_data`
  volume and `cp`-ing them over `/app/src` at startup — that made production silently diverge from git and was
  overwriting every fix. `docker cp` into a running container is fine for a quick experiment, but it is lost on rebuild.
- Live DB lives **inside the `fitness_tracker_data` volume** (`/app/data/fitness_data.db`), not the Windows host path.
  `./sync_db_from_beelink.sh` snapshots it with SQLite's backup API.
- Services: API :8000, Streamlit admin :8501, React app :3000 (nginx proxies `/api` → FastAPI).
- `GET /health` reports schema version, API-key presence and open problems.
- Schema changes go in `src/storage/schema_migrations.py` as a new numbered migration; they run on startup.
- SQLite column names are **camelCase** in the plan tables (`weekNumber`, `startDate`, `dailyPlanId`).
- One-off maintenance: `docker exec fitness-tracker-api python -m src.utils.maintenance --help`.

---

## sync_zwift_from_beelink.sh

### Bug: `scp -r` copied directories instead of files

Fixed to use `scp *.zwo` glob per week folder. Also added `| tr -d '\r'` to strip Windows line endings from PowerShell output piped through SSH.

---

## 2026-04-26 — AI Coach had no memory of prior chat sessions

### Symptom

Coach asked the athlete to re-explain upcoming events, goals, and schedule constraints that had already been discussed in prior weeks' sessions.

### Root Cause

`build_chat_system_prompt` received workout metrics, FTP trends, and `coaching_notes.json` bullet points — but never the actual chat transcripts from prior `coach_chat_sessions` rows in the DB.

### Fix Applied

- Added `load_prior_chat_sessions(before_date, n=2)` to `WorkoutDatabase` — fetches the 2 most recent SAVED sessions before the current week.
- Added `_build_prior_sessions_context()` to `AICoachPrompts` — formats transcripts with labelled Athlete/Coach turns (truncated at 600 chars/turn).
- Wired into `_ensure_context` in `AIChatSession` so every session automatically injects the last 2 weeks' transcripts into the system prompt.

---

## 2026-04-26 — Rich Goal objects invisible during chat; stale target dates

### Symptom

Coach asked the athlete to explain upcoming events like C2C even though those goals were stored in `coaching_notes.json` with priority, target dates, and progress notes. Goal dates were ~1 year stale (2025 targets referencing 2026 events).

### Root Cause

Two separate goals systems existed side-by-side:

1. `AthleteProfile.primary_goals` — simple strings, included in `build_chat_system_prompt` via `_build_athlete_context()`
2. `Goal` objects in `coaching_notes.json` — rich structured data with priority/target_date/progress_notes, only fed into `build_workout_generation_prompt` via `_build_adaptive_coaching_context()`, **never to `build_chat_system_prompt`**

`_coaching_notes` dict in `_ensure_context` also never populated the `goals` or `achievements` keys.

### Fix Applied

- Updated stale target dates: C2C → 2026-05-15, CheddarHead → 2026-08-31, Alberta Rockies → 2026-07-04
- Marked Zwift Racing League (Jan 2025) as `completed`; removed low-quality duplicate C2C goal
- Added `_build_goals_context()` to `AICoachPrompts` — buckets goals by urgency tiers (imminent <28d, upcoming <84d, later, ongoing), computes days-until, shows latest 2 progress notes per goal
- Added goals section to `build_chat_system_prompt` (between athlete profile and training context)
- Added `goals` and `achievements` keys to `_coaching_notes` dict in `_ensure_context`

### Lesson

**Goals must be in the chat prompt, not just the plan generation prompt.** The conversation is where the athlete describes their week — if the coach doesn't know C2C is 19 days away at conversation-start, it can't ask targeted questions or direct training intelligently. Keep `target_date` fields current; stale dates cause the AI to treat past events as future ones.

---

## 2026-10-05 — Why training plateaued and good rides were scored badly (overhaul)

Every one of these was silent: a wrong key or column returned null/empty and a broad `except` hid it.

| Symptom | Root cause | Fix |
|---|---|---|
| Manual matches ignored; analyses graded against the wrong workout | `_load_proposed_workout_by_name` queried snake_case columns that don't exist; error swallowed → fell back to AI matching | Correct columns; `workouts.proposed_workout_id` FK; explicit matches never fall back |
| Coach anchored every plan at "400-500 TSS" | Weekly summary read `$.TSS` / `$.TimeTotalInHours` (0 of 707 rows have them) → every week 0 TSS → "all anomalies, use default" | Read `metrics.actual_tss` / `metrics.actual_duration` |
| TSS guidance missing from the recap | Chat prompt read `recent_weeks`, producer emits `weekly_summary` | Key fixed |
| Continuity notes partly blank / 9 months stale | Prompt read `progression`/`monitor`/`next_priorities`; data uses `progression_notes`/... ; writer path never called | Field names fixed; continuity stored in DB after every saved plan |
| HR/IF trends empty | `average_hr`/`max_hr`/`intensity_factor` paths; data uses `average`/`max`/`if` | Paths fixed |
| Recap ran on Haiku | Model selector defaulted to index 1 when no GITHUB_TOKEN | Opus 5 default; GitHub path removed |
| Progression never happened | No CTL/ATL model, no ramp, no progression memory; prompt said "MAXIMIZE VARIETY / don't repeat types" | `training_load.py`, `periodization.py` (computed band enforced on generation), `progression.py` ledger; prompt now progresses within a type |
| Perfect ERG rides scored 4-7/10 | Wrong plan + LLM grading from prose; lap markers never stored | `erg_execution.py` computes the score from laps/time series; LLM narrates it |

**Lessons:** run `json_extract`/column names against the real DB before trusting a query; never catch
broad exceptions around data lookups; record background failures with `record_event` (shown in the UI sidebar)
instead of `print` on a headless box; compute anything numeric instead of asking an LLM to judge it.

---

## 2026-10-06 — Strength workouts missing; re-imports undid the review

- **TrainingPeaks structured strength workouts are not in the Workout Summary CSV.** They live in a separate
  service (`api.peakswaresb.com/rx/activity/...`, own auth). The sync opens the calendar, captures that response
  and appends the completed sessions to the CSV before upload (`strength_csv_rows` / `append_strength_rows`).
- **`POST /upload/workouts` deletes and re-inserts its date range.** The live `workouts.id` has no AUTOINCREMENT,
  so re-inserted rows reused ids in export order: matches were wiped and analyses detached or landed on the wrong
  workout. The nightly 3-day re-import made this routine. `snapshot_workouts` / `restore_workouts` now put back
  ids, matches and notes; `reattach_orphan_analyses` repairs by ride file. Test: `tests/test_reimport.py`.
- **Lesson:** anything that deletes and re-inserts rows must carry user-owned columns and ids across, and must be
  tested by running it twice.
