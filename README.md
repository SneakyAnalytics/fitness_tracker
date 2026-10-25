<p align="center">
  <img src="docs/images/banner.jpg" alt="Coach Claude: computed training load, measured execution, and an AI coach that plans inside the numbers" width="100%">
</p>

<p align="center">
  <a href="https://github.com/SneakyAnalytics/fitness_tracker/actions/workflows/docker.yml"><img alt="Build" src="https://github.com/SneakyAnalytics/fitness_tracker/actions/workflows/docker.yml/badge.svg"></a>
  <img alt="Python 3.12" src="https://img.shields.io/badge/Python-3.12-2c5f2d?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-API-2c5f2d?logo=fastapi&logoColor=white">
  <img alt="React 19" src="https://img.shields.io/badge/React-19-4a7c7e?logo=react&logoColor=white">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-13_migrations-4a7c7e?logo=sqlite&logoColor=white">
  <img alt="Claude Opus 5" src="https://img.shields.io/badge/Claude-Opus_5_·_tool_use-b8956a">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-GHCR_images-4a7c7e?logo=docker&logoColor=white">
</p>

<p align="center">
  <b><a href="#-the-sports-science">The science</a></b> ·
  <b><a href="#-the-ai-coach">The AI coach</a></b> ·
  <b><a href="#-architecture">Architecture</a></b> ·
  <b><a href="#-field-notes-what-the-data-taught-me">Field notes</a></b> ·
  <b><a href="#-running-it">Running it</a></b>
</p>

---

**Coach Claude** is the training system I train with every day. It pulls my rides, runs, strength sessions and Garmin biometrics from TrainingPeaks every night. It also:

- models fitness and fatigue
- scores how precisely each structured workout was executed
- prescribes next week's training with an AI coach that works inside the numbers rather than inventing them
- writes the week as Zwift workout files that land on my bike computer at 5 AM Monday

It began as a weekend project in January 2025. I rebuilt it in October 2026 after noticing that rides from a year earlier felt harder than the current ones. That turned out to be true. The cause was that **an LLM was choosing my weekly training load with no computed training state to anchor it**, and the plans had become a random walk.

> **The principle the rebuild is built on:** compute everything that can be computed. Fitness, fatigue, ramp rate, execution quality and FTP are deterministic. The language model reasons, asks questions and explains, but it works inside numbers it is handed and never grades or invents them.

| 20 months | 727 | 708 | 5,772 | 798 | 66 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| continuous data, Feb 2025 → today | completed workouts | FIT files parsed (Zwift + Garmin) | daily biometric records (HRV · RHR · sleep · Body Battery) | prescribed sessions across 82 planned weeks | automated tests run on every push |

<p align="center">
  <img src="docs/images/calendar.jpg" alt="Training calendar: a completed week with execution scores on each structured session, commutes and saunas recorded as unplanned" width="100%">
  <br><sub><i>A completed week: each structured ride carries its computed execution score; commutes, saunas and strength are matched to the plan or marked as unplanned.</i></sub>
</p>

---

## 🔬 The sports science

### 1. Training load: the Performance Manager model

Daily Training Stress Score (TSS) feeds two exponentially weighted moving averages. They are the Coggan Performance Manager simplification of Banister's impulse-response model:

$$
\text{CTL}_t = \text{CTL}_{t-1} + \frac{\text{TSS}_t - \text{CTL}_{t-1}}{42}
\qquad
\text{ATL}_t = \text{ATL}_{t-1} + \frac{\text{TSS}_t - \text{ATL}_{t-1}}{7}
\qquad
\text{TSB}_t = \text{CTL}_{t-1} - \text{ATL}_{t-1}
$$

- **CTL** is chronic load, or "fitness".
- **ATL** is acute load, or "fatigue".
- **TSB** is "form".

The series is rebuilt from all of history into `training_load_daily` after every sync ([`training_load.py`](src/utils/training_load.py)). TSS comes from TrainingPeaks, never from the language model.

### 2. Periodization: next week's load is derived, not invented

[`periodization.py`](src/utils/periodization.py) turns the current state into a hard TSS band for next week:

- **Build weeks:** the band is solved analytically for a **CTL ramp of +2 to +4 per week** (see the formula below).
- **Recovery weeks:** after **3 consecutive build weeks**, the band drops to **60–70 %** of the recent average (a 3:1 mesocycle).
- **Tapers:** load steps down into dated goal events from the goals table.

Holding a constant daily load $d$ for 7 days moves CTL to $\text{CTL}\cdot k + d(1-k)$, where $k = (1-\tfrac{1}{42})^7$. So the weekly load for a target CTL change $\Delta$ is

$$
\text{TSS}_{\text{week}} = 7 \cdot \frac{\text{CTL} + \Delta - \text{CTL}\cdot k}{1-k}
$$

The coach plans inside this band, and every generated plan is **checked against it**. A plan outside the band goes back to the model to fix, and is flagged before saving if it still misses. Under the old system, planned load swung 550 → 300 → 480 TSS from week to week.

### 3. Execution scoring: measured, not judged

The original system asked a model to rate each ride from a prose description. Perfectly executed ERG rides came back 4–7/10. [`erg_execution.py`](src/utils/erg_execution.py) now **measures** execution instead:

<table>
<tr>
<td width="55%" valign="top">

- **Alignment.**
  - Zwift stamps a FIT lap at every `.zwo` interval boundary. Laps are paired with prescribed intervals by duration, trying every count of leading extra laps, and accepted only if durations agree within 10 %.
  - Without laps, the prescribed power profile is **slid along the 1 Hz power series** to the offset with the least error, so a pre-ride spin doesn't shift every interval.
- **Deviation.**
  - Deviation is **0 inside the target band**. Outside it, deviation is the percentage beyond the nearest band edge.
  - Points per interval: ≤ 5 % → 1.0, ≤ 10 % → 0.7, ≤ 20 % → 0.3, otherwise 0.
  - The score is the **duration-weighted** mean over work intervals, out of 10.
- **Systematic-offset detection.** ERG mode holds *fraction × Zwift's FTP*. If every work interval misses in the same direction by ≥ 2 % with ≤ 2 % spread, the cause is an FTP-setting mismatch, not the rider. The offset is removed before scoring and reported separately.
- **Narration.** The computed numbers go to Claude Sonnet as facts, and it writes the narrative. Every interval is persisted in `interval_results` (526 so far).

</td>
<td width="45%" valign="top">
<img src="docs/images/execution.jpg" alt="Target power band versus actual power for a 3x15 minute sweet spot session, with an interval-by-interval deviation table" width="100%">
</td>
</tr>
</table>

### 4. Which FTP the plan is written against

Zwift scales every `.zwo` by **its own** FTP, ignores `<ftpOverride>`, and only changes it after a ramp test or race. So a plan written against a different FTP produces watts that never match.

[`zwift_ftp.py`](src/utils/zwift_ftp.py) recovers Zwift's FTP from the rides themselves. Each FIT record carries the ERG `target_power`, and the system knows which FTP fraction it wrote for that interval:

$$
\text{FTP}_{\text{Zwift}} \approx \frac{\overline{\text{target watts}}}{\overline{\text{prescribed fraction}}}
$$

The app's FTP follows that value automatically. A Zwift FTP unchanged for 6 weeks raises a "test due" flag.

### 5. Progression, power curve and readiness

| Signal | How it's computed | Why it matters |
|---|---|---|
| **Progression ledger** | Every structured ride is classified by archetype (threshold, sweet spot, VO2max, over/under, tempo, endurance). For each one it records work-interval structure, average watts, normalized power, %FTP and execution score ([`progression.py`](src/utils/progression.py)). | The coach sees a trajectory such as `3×12 @ 279W → 3×15 @ 284W` instead of an aggregate, and can progress *within* a type. Silent regressions become visible. |
| **Mean-max power curve** | Best rolling 5 s / 1 m / 5 m / 20 m / 60 m power per ride, compared over 90-day windows against the same window a year earlier. | Answers "am I fitter than last year?" with data. It also feeds a power-curve FTP estimate that flags divergence from the working FTP. |
| **Readiness** | Last 7 days of HRV, resting HR, sleep and Body Battery against a **60-day median baseline**, with plain-language flags (for example HRV ≤ −10 % or RHR ≥ +5 %). | Lets the coach tell a strategic recovery week from a reactive one. |

<p align="center">
  <img src="docs/images/dashboard.jpg" alt="Training dashboard: CTL, ATL, TSB, ramp rate, Zwift FTP and readiness tiles; weekly TSS and CTL charts; best power over 90 days; progression tables per workout archetype" width="75%">
  <br><sub><i>The dashboard: load and readiness tiles, weekly TSS against end-of-week CTL, the 90-day power curve, and progression for each workout type.</i></sub>
</p>

---

## 🧠 The AI coach

The weekly session runs on **Claude Opus 5 with tool use**, so it looks things up instead of relying on whatever was packed into one giant prompt. It streams over Server-Sent Events, with the large, stable system prompt cached between turns.

| Tool | Answers |
|---|---|
| `get_training_load` | CTL / ATL / TSB over any range |
| `get_progression` | the archetype ledger above |
| `compare_to_period` | "how does now compare with *n* weeks ago?" |
| `get_readiness` | HRV / RHR / sleep against baseline |
| `get_week_detail`, `get_workout_intervals` | any week or interval-level ride |
| `search_prior_conversations` | earlier coaching sessions, so it doesn't ask twice |
| `get_goals`, `save_goal`, `update_goal` | the goals table: dated events with taper awareness |

**The Sunday loop**

1. **Review:** confirm the week's suggested matches between completed and planned sessions.
2. **Coach:** the coach recaps the week, checks load, readiness and progression, and asks two or three questions.
3. **Plan:** it writes next week inside the computed band. You ask for changes in plain language.
4. **Save:** the plan becomes Zwift `.zwo` files, plus guided strength and mobility sessions with per-movement timers in the app.

During the week, any day can be opened to **ask the coach about that session**, for example fueling, a shorter substitute, or "what is this movement?"

<p align="center">
  <img src="docs/images/review.jpg" alt="Weekly review step: each completed session confirmed against its planned workout, with execution scores" width="88%">
</p>

---

## 🏗 Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#eef3ec', 'primaryTextColor': '#1e4620', 'primaryBorderColor': '#2c5f2d', 'lineColor': '#4a7c7e', 'clusterBkg': '#f5f5f0', 'clusterBorder': '#b8956a', 'edgeLabelBackground': '#f5f5f0'}}}%%
flowchart LR
    subgraph Sources
        TP[TrainingPeaks<br/>web export]
        RX[TrainingPeaks<br/>strength feed]
        FIT[Garmin + Zwift<br/>FIT files]
    end

    subgraph Beelink["Home server (Windows · Docker)"]
        SYNC[Nightly sync<br/>Playwright, 22:30]
        LINK[Matcher<br/>Pacific date · sport aware]
        DB[(SQLite<br/>13 versioned migrations)]
        CALC[Training state<br/>load · periodization ·<br/>execution · readiness]
        API[FastAPI<br/>REST + SSE]
        WEB[React 19 app<br/>nginx]
        ADMIN[Streamlit admin]
    end

    LLM[Claude Opus 5<br/>tool use]
    ZW[Zwift on the Mac<br/>.zwo at 05:00]

    TP & RX & FIT --> SYNC --> LINK --> DB
    DB <--> CALC
    CALC --> API
    DB <--> API
    API <--> LLM
    API --> WEB
    API --> ADMIN
    API -- weekly plan --> ZW
```

| Layer | Stack |
|---|---|
| Ingestion | Playwright (headless TrainingPeaks export + strength feed), `fitparse` for FIT, pandas |
| Storage | SQLite with an ordered migration runner and a `schema_version` table |
| Computation | Plain Python: no LLM in the numeric path |
| API | FastAPI: REST, Server-Sent Events for the coach, background jobs for sync and save |
| Frontend | React 19, Vite, TanStack Query, Recharts; Streamlit kept as an admin surface |
| AI | Claude Opus 5 (coach, tool use, prompt caching), Claude Sonnet 5 (planned-ride narratives), Gemini (unplanned rides over an hour) |
| Delivery | GitHub Actions runs the tests, builds images and pushes them to GHCR. The server **pulls** a pinned commit, backs up the database first, and health-checks after. |
| Operations | Nightly sync, 05:00 Zwift delivery, a 10-minute Docker watchdog, and background failures surfaced in the UI |

---

## 📓 Field notes: what the data taught me

Every one of these bugs was **silent**: a wrong key or column returned null, and a broad `except` hid it. They are the most transferable thing in this repo. The full post-mortems are in [`AGENTS.md`](AGENTS.md).

- **Manual matches were discarded for months.** A lookup queried snake_case columns in a camelCase schema, the error was swallowed, and every ride was re-matched by an AI guess and graded against the wrong workout. **Lesson:** run every query against the real schema, and never catch broad exceptions around data lookups.
- **Every week looked like 0 TSS** to the planner, because the summary read `$.TSS` while the data stored `metrics.actual_tss`. The model "corrected" for the anomaly with a default 400–500 TSS. **Lesson:** a model will happily reason from a broken input; validate inputs before they reach the prompt.
- **UTC vs local time.** Garmin and Zwift record UTC, but TrainingPeaks days are Pacific. Evening commutes were attached to the next day's sessions. **Lesson:** convert to the athlete's local date before any join.
- **A read path that wrote.** A weekly summary "helpfully" attached any same-day FIT file to sessions without one and saved the link. A sauna inherited a 4-hour gravel ride, and the coach saw 735 TSS for a 520 TSS week. **Lesson:** derived joins belong in one matcher; summaries must be read-only.
- **Re-imports must keep identity.** The nightly re-import deletes and re-inserts rows. Without restoring ids and user decisions, it silently undid the athlete's Sunday review and detached analyses. **Lesson:** test idempotency by running everything twice.
- **Ask the data before tuning the prompt.** The "coaching doesn't progress" complaint looked like a prompt problem. It was a missing model of training load. Compute the state, then let the model reason over it.

---

## 🚀 Running it

```bash
# API (http://localhost:8000) and admin (http://localhost:8501)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # TrainingPeaks + API keys
uvicorn src.api.app:app --reload
streamlit run src/ui/streamlit_app.py

# Training app (http://localhost:5173, proxies /api to :8000)
cd frontend && npm install && npm run dev

# Tests
pytest -q && (cd frontend && npm test)
```

Production deployment, rollback, and Windows/WSL stability notes are in the [runbook](docs/deployment/RUNBOOK.md). One-off maintenance (relinking FIT files, recomputing derived data) runs through `python -m src.utils.maintenance --help`.

<details>
<summary><b>Repository map</b></summary>

```
src/
  api/            FastAPI app + coach/review/dashboard routes (SSE)
  storage/        SQLite access, versioned migrations, FIT matching, goals, events
  utils/
    training_load.py    CTL/ATL/TSB, power curve, FTP estimate, readiness
    periodization.py    next week's TSS band (ramp, 3:1 deload, taper)
    erg_execution.py    lap/time-series alignment and execution scoring
    zwift_ftp.py        Zwift FTP from ERG targets
    progression.py      per-archetype progression ledger
    coach_tools.py      tools exposed to the coach
    ai_chat_session.py  the weekly coaching session
    trainingpeaks_sync.py, nightly_sync.py, week_review.py
  ui/             Streamlit admin
frontend/         React 19 training app (calendar, coaching, dashboard)
tests/            pytest suite (54) · frontend/src/**/*.test.js (12)
docs/             runbook, architecture notes, images
```
</details>

---

<p align="center">
  <sub>Built and ridden in the Pacific Northwest 🌲 · by <a href="https://github.com/SneakyAnalytics">Jacob Robinson</a></sub>
</p>
