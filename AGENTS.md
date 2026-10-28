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

- **This repository is public. Never commit machine- or network-specific details**: server addresses, usernames, home folders, SSH keys,
  emails, API keys. Put them in the git-ignored `deploy.local.env` (read by the Mac-side scripts; template: `deploy.local.env.example`),
  `AGENTS.local.md` (private notes for agents on this machine) or `.env`. In anything committed use placeholders (`<user>`, `<beelink-ip>`,
  `%USERPROFILE%`). `tests/test_no_local_info.py` fails if one slips in. Host-side scripts derive paths from `$env:USERPROFILE`.
- Beelink is **Windows** (`C:/Users/<user>/...`) with **no rsync or git** — only `tar`, `scp`, Docker Compose.
- Deploy: push to `main` → GitHub Actions tests and publishes images to ghcr.io →
  `./deploy_to_beelink.sh` pulls them (backs up the DB first, health-checks after).
  Full procedure, rollback and Windows/WSL stability notes: `docs/deployment/RUNBOOK.md`.
- Containers run code **from the image only**. Do NOT go back to copying `.py` files into the `fitness_tracker_data`
  volume and `cp`-ing them over `/app/src` at startup — that made production silently diverge from git and was
  overwriting every fix. `docker cp` into a running container is fine for a quick experiment, but it is lost on rebuild.
- Live DB lives **inside the `fitness_tracker_data` volume** (`/app/data/fitness_data.db`), not the Windows host path.
  `./sync_db_from_beelink.sh` snapshots it with SQLite's backup API.
- Services: API :8000, React app :3000 (nginx proxies `/api` → FastAPI). Maintenance (problems, ride files, goals, Zwift files) is the React `/admin` page. The Streamlit admin was retired; its last commit is tagged `streamlit-final`.
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

## 2026-10-05 — Data-quality lessons: computed training state and measured execution

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

---

## 2026-10-10 — Docker Desktop died 72 hours after being started

- The "Start Docker Desktop" scheduled task launches Docker Desktop as the task's own process, and Task
  Scheduler's default `ExecutionTimeLimit` is 72 hours. Started 2026-10-06 ~06:10, Docker was killed 2026-10-09
  ~06:10; the app was down ~38 h and the nightly/Zwift tasks just failed. No reboot, no crash event.
- Fix: `scripts/register_docker_watchdog.ps1` sets the limit to unlimited (`PT0S`) and registers
  `FitnessTrackerDockerWatchdog` (every 10 min) to restart Docker and the containers.
- **Lesson:** any scheduled task that *is* a long-running process needs `ExecutionTimeLimit` disabled; and
  "nothing is running" must be detected by something other than the things that need Docker.

---

## 2026-10-11 — Coach reported 735 TSS for a 520 TSS week

- `generate_weekly_summary` "fell back" to any FIT file stored under the same day for sessions without one,
  **and saved that link**. FIT files are stored under their UTC upload date, so Sunday's sauna took Saturday's
  4-hour gravel file (uploaded after midnight UTC); the summary used the file's TSS/duration (its duration even
  ahead of TrainingPeaks'), counting the ride twice. Fallback removed; summary prefers TrainingPeaks' numbers.
- The upload grouped FIT files by UTC date, and the linker matched Garmin files on duration alone, so evening
  commutes landed on the next day and a 45-min yoga swapped files with a 45-min ride. Both now use the Pacific
  date and `sport_compatible` (bike ↔ cycling file, everything else ↔ non-cycling, sauna ↔ none).
- `repair_fit_links` (also `maintenance repair-fit-links`) runs after every upload: drops cross-day,
  wrong-sport and shared links, relinks, and removes analyses made from a file the workout no longer holds.
- Periodization/CTL were unaffected: they read `training_load_daily`, built from TrainingPeaks TSS.
- **Lesson:** a read path (a summary) must never write links; derived "best guess" joins belong in one matcher.

---

## 2026-10-26 — Retiring Streamlit and adding the new pages: three things that bit

- **Removing a dependency can remove ones you use without declaring.** `pandas` and `numpy` were only installed because
  `streamlit` pulled them in; CI failed on the first push without it (local tests passed because the venv still had them).
  Before dropping a package, build a clean venv from `requirements.txt` and run the tests and an import of every module.
- **`position: fixed` is relative to the nearest transformed ancestor.** The page-transition wrapper has a `transform`, so a
  "full-screen" overlay (gym mode) rendered inside the page was clipped to it. Render overlays with a React portal on `<body>`.
- **Recharts wrappers must not be constrained with `max-width: 100%`.** `.recharts-wrapper` collapsed to 0 px wide and the
  chart was blank while its SVG, axes and lines all "existed". If a chart is empty, compare `.recharts-wrapper` width with a
  working chart before suspecting the data. (Shared axes also need to be real children of the chart, not a fragment.)
- `deploy_to_beelink.sh` deploys whatever `origin/main` is *now*: pushing again while waiting for images makes it fail with
  "not found". Wait for the images of the newest commit.

---

## 2026-10-27 — A refactor dropped an import and broke strength saves and interval charts for a day

- **Symptom:** gym mode / the exercise list said it could not reach the API when saving weights and reps; the interval chart
  on completed rides in the calendar was also dead. The server was fine (a direct POST returned 200).
- **Root cause:** moving `useWeek`/`useWeather` out of `WorkoutCalendar.jsx` replaced the `workoutAPI` import line, so
  `workoutAPI.savePerformance`, `.getPerformance` and `.getIntervals` threw `ReferenceError`. Axios errors without a
  `response` looked identical to a network failure in the UI message. Neither the build nor the tests noticed.
- **Fix:** import restored; `src/imports.test.js` now runs ESLint (`no-undef`, `react/jsx-no-undef` only) over `src/`, so a
  missing import fails `npm test` and CI. Verified by deleting the import: the test names the three lines.
- **Also learned:** logs were keyed by the exercise's *position* and the coach never read them. They are now indexed by
  name (`strength_log`, migration 16, backfilled) and fed to the coach. Older free-text entries hold one number for the
  whole exercise ("24" for 3 x 8); those are flagged `total` and never trigger an automatic weight increase.
- **Lesson:** after a refactor that moves code between files, exercise the feature in a browser, not just the build. And keep
  user-facing error text honest: only blame the network when there actually was no response.

---

## 2026-10-28 — An over-under was recorded as "1 x 7 min at 194 W"

- **Symptom:** the dashboard showed the Oct 27 over-under as a 110 W drop from the one before. The ride itself was fine
  (execution score 10, every segment matched its target).
- **Root cause:** `pick_work` only counted single intervals of 4+ minutes. That plan wrote each block as 2 min under / 1 min
  over pieces (five per block), so no piece qualified and the only 4+ minute interval left was the 7-minute easy spin-out.
- **Fix:** consecutive hard pieces are merged into one block before the 4-minute test, starting from the highest prescribed
  intensity and stepping down until a sustained block exists (so a sprint can't hide the work). Rebuilt on the real data:
  4 x 8 min at 303.6 W against a 304.9 W target. A rebuild also corrected ~20 older rows (over-unders from May to August now
  show their real block sizes; steady rides split into segments read as one block).
- **Lesson:** an aggregation written against one plan format silently misreads another. When the ledger looks wrong, check
  `GET /workouts/<id>/intervals` first: if the intervals are right and the summary is wrong, the picker is the bug.
  After changing it, rebuild a copy of the DB and diff every row before shipping.
