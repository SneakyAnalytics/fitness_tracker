"""Coach endpoints for the React app.

Streaming endpoints return Server-Sent Events: each event is a JSON object,
{"type": "text", "text": ...}, {"type": "status", "text": ...}, then a final
{"type": "done", ...} (or {"type": "error", ...}).
"""
from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime, timedelta
from typing import Any, Dict, Generator, Iterable, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.storage.database import WorkoutDatabase
from src.utils import progression, training_load, zwift_ftp
from src.utils.ai_coach_config import AIModel

router = APIRouter()

WEEKLY_MODELS = {m.name: m for m in (AIModel.CLAUDE_OPUS, AIModel.CLAUDE_SONNET, AIModel.CLAUDE_HAIKU,
                                     AIModel.GEMINI_FREE)}
ASK_MODEL = AIModel.CLAUDE_SONNET  # quick in-workout questions

# One live session object per week keeps the (expensive) context between turns.
_sessions: Dict[str, Any] = {}
_sessions_lock = threading.Lock()


def _monday(value: str) -> str:
    d = datetime.strptime(value[:10], "%Y-%m-%d").date()
    return (d - timedelta(days=d.weekday())).isoformat()


def _session(week_start: str, model_name: str = "CLAUDE_OPUS"):
    from src.utils.ai_chat_session import AIChatSession
    from src.utils.ai_coach_engine import AICoachEngine

    model = WEEKLY_MODELS.get(model_name)
    if model is None:
        raise HTTPException(status_code=400, detail=f"model must be one of {list(WEEKLY_MODELS)}")
    key = _monday(week_start)
    with _sessions_lock:
        session = _sessions.get(key)
        if session is None or session._coach.model != model:
            session = AIChatSession.load_or_create(key, WorkoutDatabase(), AICoachEngine(model=model))
            _sessions[key] = session
        return session


def _sse(events: Iterable[Dict[str, Any]]) -> StreamingResponse:
    def body():
        try:
            for event in events:
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except HTTPException:
            raise
        except Exception as exc:  # surface failures to the client instead of a dead stream
            from src.storage.events import record_event
            record_event("error", "coach_api", f"Streaming request failed: {exc}")
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"
    # X-Accel-Buffering stops nginx from batching the stream.
    return StreamingResponse(body(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _session_events(session, chunks: Iterable[str]) -> Generator[Dict[str, Any], None, None]:
    for chunk in chunks:
        if chunk:
            if chunk.startswith("\n\n_🔎 "):
                yield {"type": "status", "text": chunk.strip().strip("_").replace("🔎 ", "")}
            else:
                yield {"type": "text", "text": chunk}
    session.persist()
    yield {"type": "done", "phase": session.phase, "has_plan": bool(session.current_plan),
           "cost": round(session._coach.session_cost, 4)}


def _session_state(session) -> Dict[str, Any]:
    return {"week_start": session.week_start_date, "phase": session.phase,
            "messages": session.messages, "current_plan": session.current_plan}


class WeekRequest(BaseModel):
    week_start: str
    model: str = "CLAUDE_OPUS"


class MessageRequest(WeekRequest):
    message: str = Field(min_length=1)


class EditRequest(WeekRequest):
    feedback: str = Field(min_length=1)


@router.get("/coach/session")
def get_session(week_start: str, model: str = "CLAUDE_OPUS"):
    return _session_state(_session(week_start, model))


def _require_finished_week(week_start: str) -> None:
    sunday = datetime.strptime(_monday(week_start), "%Y-%m-%d").date() + timedelta(days=6)
    if sunday > date.today():
        raise HTTPException(status_code=400,
                            detail=f"That week isn't over yet — the recap opens on Sunday {sunday:%b %d}.")


@router.post("/coach/session/begin")
def begin_session(req: WeekRequest):
    _require_finished_week(req.week_start)
    s = _session(req.week_start, req.model)
    week_end = (datetime.strptime(s.week_start_date, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
    return _sse(_session_events(s, s.begin_analysis(week_end)))


@router.post("/coach/session/message")
def send_message(req: MessageRequest):
    s = _session(req.week_start, req.model)
    return _sse(_session_events(s, s.chat(req.message)))


@router.post("/coach/session/generate")
def generate_plan(req: WeekRequest):
    s = _session(req.week_start, req.model)
    week_end = (datetime.strptime(s.week_start_date, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
    return _sse(_session_events(s, s.generate_plan(week_end)))


@router.post("/coach/session/edit")
def edit_plan(req: EditRequest):
    s = _session(req.week_start, req.model)
    return _sse(_session_events(s, s.apply_surgical_edit(req.feedback)))


# Saving writes the plan, then builds the Zwift files (fetching news text for each),
# which can take several minutes, so it runs in the background and the page polls.
_saves: Dict[str, Dict[str, Any]] = {}


@router.post("/coach/session/save")
def save_plan(req: WeekRequest):
    s = _session(req.week_start, req.model)
    if not s.current_plan:
        raise HTTPException(status_code=400, detail="No plan to save")
    key = _monday(req.week_start)
    with _sessions_lock:
        if (_saves.get(key) or {}).get("state") == "running":
            return _saves[key]
        _saves[key] = {"state": "running", "started": datetime.now().isoformat(timespec="seconds")}
    zwift_dir = os.getenv("ZWIFT_WORKOUTS_DIR", "shareable/zwift_workouts")

    def run():
        from src.storage.events import record_event
        try:
            ok, message, files = s.save_plan(zwift_dir)
            _saves[key] = {"state": "done" if ok else "error", "message": message, "zwift_files": files}
            if not ok:
                record_event("error", "coach_save", f"Saving the plan failed: {message}")
        except Exception as exc:
            _saves[key] = {"state": "error", "message": str(exc)}
            record_event("error", "coach_save", f"Saving the plan failed: {exc}")

    threading.Thread(target=run, daemon=True).start()
    return _saves[key]


@router.get("/coach/session/save")
def save_status(week_start: str):
    return _saves.get(_monday(week_start)) or {"state": "idle"}


# ── Ask the coach about a specific day's workout ─────────────────────────────

class AskTurn(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    date: str
    question: str = Field(min_length=1)
    history: List[AskTurn] = []


def _day_context(day: str, db: WorkoutDatabase) -> str:
    week = db.get_all_workouts_for_week(day, day)
    planned = week["proposed_workouts"]
    done = week["completed_workouts"]
    lines = [f"# The athlete is asking about {day}"]
    if planned:
        lines.append("## Planned")
        for p in planned:
            lines.append(f"- {p['name']} ({p['type']}, {p.get('plannedDuration')} min, "
                         f"TSS {p.get('plannedTSS_min')}-{p.get('plannedTSS_max')})")
            if p.get("intervals"):
                lines.append(f"  intervals: {p['intervals']}")
            if p.get("sections"):
                lines.append(f"  sections: {p['sections']}")
            if p.get("notes"):
                lines.append(f"  notes: {p['notes']}")
    if done:
        lines.append("## Already completed that day")
        for w in done:
            lines.append(f"- {w['title']} (TSS {(w.get('metrics') or {}).get('actual_tss')})")
    return "\n".join(lines)


ASK_SYSTEM = """You are the athlete's cycling coach (the same coach who writes their weekly plans),
answering a quick question about one day's workout from their phone or the trainer.
The question is about {day_label}; today is {today_label}. Keep the two straight
(e.g. a question about Saturday asked on Monday is planning ahead).

Typical questions: fueling for the session, what a movement is or how to do it, a substitute
when they're short on time or equipment, how hard a block should feel, or whether to go
ahead given how they feel. Be practical and short (under ~150 words unless they ask for
detail). If you substitute a workout, keep the session's purpose and give concrete
structure (durations, watts from their FTP, sets/reps). Use tools when history or
readiness matters; don't ask them for information you can look up.

Athlete FTP: {ftp}W.

{training_state}

{day_context}"""


@router.post("/coach/ask")
def ask_coach(req: AskRequest):
    from anthropic import Anthropic
    from src.utils.ai_coach_config import AICoachConfig
    from src.utils.coach_context import build_training_state
    from src.utils.coach_tools import stream_tool_conversation

    key = AICoachConfig().claude_api_key
    if not key:
        raise HTTPException(status_code=503, detail="CLAUDE_API_KEY is not configured")
    db = WorkoutDatabase()
    ftp = (db.get_athlete_settings() or {}).get("ftp")
    state, _ = build_training_state(_monday(req.date), ftp, db.db_path, refresh=False)
    day = datetime.strptime(req.date[:10], "%Y-%m-%d").date()
    system = ASK_SYSTEM.format(ftp=ftp, training_state=state, day_context=_day_context(req.date[:10], db),
                               day_label=f"{day:%A %Y-%m-%d}", today_label=f"{date.today():%A %Y-%m-%d}")
    messages = [{"role": t.role, "content": t.content} for t in req.history if t.role in ("user", "assistant")]
    messages.append({"role": "user", "content": req.question})
    client = Anthropic(api_key=key)

    def events():
        result: Dict[str, Any] = {}
        for kind, value in stream_tool_conversation(client.messages, {}, ASK_MODEL.value, system, messages,
                                                    db_path=db.db_path, max_tokens=8000, result=result):
            yield {"type": kind, "text": value}
        yield {"type": "done", "answer": result.get("text", "")}

    return _sse(events())


# ── Dashboard ────────────────────────────────────────────────────────────────

def _goal_medals(db_path: str) -> Dict[str, Any]:
    """Completed goals (newest first) and the next dated target, for the dashboard's Achievements strip."""
    from src.storage import goals as goals_store
    rows = goals_store.list_goals(include_inactive=True, db_path=db_path)
    done = []
    for g in rows:
        if g["status"] != "completed":
            continue
        # events carry their own date; open-ended goals fall back to when they were ticked off
        when = (g.get("target_date") or (g.get("updated_at") or "")[:10] or None)
        done.append({"id": g["id"], "description": g["description"], "category": g.get("category"), "date": when})
    done.sort(key=lambda d: d["date"] or "", reverse=True)
    upcoming = [g for g in rows if g["status"] == "active" and g.get("days_until") is not None and g["days_until"] >= 0]
    upcoming.sort(key=lambda g: g["days_until"])
    nxt = ({"id": upcoming[0]["id"], "description": upcoming[0]["description"],
            "date": upcoming[0]["target_date"], "days_until": upcoming[0]["days_until"]} if upcoming else None)
    return {"completed": done, "next": nxt}


# A week "hits" when the TSS actually ridden lands within 15 % of the plan's band.
HIT_LOW, HIT_HIGH = 0.85, 1.15


def week_status(tss: float, planned_min: Optional[float], planned_max: Optional[float]) -> str:
    if not planned_min or not planned_max:
        return "none"
    return "hit" if planned_min * HIT_LOW <= tss <= planned_max * HIT_HIGH else "miss"


def _consistency(db_path: str, weeks: int = 12) -> Dict[str, Any]:
    """Per-week plan adherence and the current streak of consecutive hit weeks."""
    import sqlite3
    rows = training_load.weekly_load(db_path, weeks=weeks)
    conn = sqlite3.connect(db_path)
    try:
        plans = {r[0]: (r[1], r[2]) for r in conn.execute(
            "SELECT startDate, plannedTSS_min, plannedTSS_max FROM weekly_plans")}
    finally:
        conn.close()
    out = []
    for r in rows:
        lo, hi = plans.get(r["week_start"], (None, None))
        out.append({"week_start": r["week_start"], "tss": r["tss"], "planned_min": lo, "planned_max": hi,
                    "status": week_status(r["tss"], lo, hi)})
    streak = 0
    for w in reversed(out):
        if w["status"] != "hit":
            break
        streak += 1
    return {"weeks": out, "streak": streak}


class ConfirmFtp(BaseModel):
    ftp: int = Field(ge=100, le=600)
    date: Optional[str] = None


@router.post("/zwift_ftp/confirm")
def confirm_zwift_ftp(req: ConfirmFtp):
    """The athlete read their FTP off Zwift (after a ramp test): record it so the app follows it."""
    try:
        return zwift_ftp.confirm_ftp(req.ftp, req.date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _wkg_target(db_path: str) -> Optional[float]:
    """The W/kg figure in an active goal such as "Achieve 4.0+ W/kg", if there is one."""
    import re
    from src.storage import goals as goals_store
    for g in goals_store.list_goals(db_path=db_path):
        m = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*W/kg", g["description"], re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


@router.get("/dashboard/trends")
def dashboard_trends(weeks: int = 16):
    db = WorkoutDatabase()
    ftp = (db.get_athlete_settings() or {}).get("ftp")
    return {
        "load": training_load.load_snapshot(db.db_path),
        "weekly": training_load.weekly_load(db.db_path, weeks=weeks),
        "load_projection": training_load.project_load(db.db_path),
        "power_curve": training_load.compare_power_curves(90, db_path=db.db_path),
        "power_profile": training_load.power_profile(db.db_path),
        "zwift_ftp": zwift_ftp.current(db.db_path),
        "power_to_weight": training_load.power_to_weight(
            (zwift_ftp.current(db.db_path) or {}).get("ftp") or ftp, _wkg_target(db.db_path), db.db_path),
        "readiness": training_load.readiness(db_path=db.db_path),
        "readiness_series": training_load.readiness_series(db_path=db.db_path),
        "goals": _goal_medals(db.db_path),
        "consistency": _consistency(db.db_path, weeks=12),
        "progression": {a: progression.get_progression(a, 6, db.db_path)
                        for a in ("threshold", "sweet_spot", "over_under", "vo2max", "tempo", "endurance")},
    }


@router.get("/workouts/{workout_id}/intervals")
def workout_intervals(workout_id: int):
    """Computed prescribed-vs-actual rows for a completed workout (may be empty)."""
    import sqlite3
    db = WorkoutDatabase()
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT interval_index, name, label, duration_sec, target_low_w, target_high_w, actual_avg_w,"
            " deviation_pct, compliance, alignment FROM interval_results WHERE workout_id = ? ORDER BY interval_index",
            (workout_id,)).fetchall()
    finally:
        conn.close()
    from src.utils.progression import work_summary
    intervals = [dict(r) for r in rows]
    return {"workout_id": workout_id, "intervals": intervals, "work": work_summary(intervals)}


# ── Weekly review: import + confirm matches ─────────────────────────────────

class MatchRequest(BaseModel):
    workout_id: int
    proposed_workout_id: Optional[int] = None
    label: Optional[str] = None
    note: Optional[str] = Field(None, max_length=500)    # why this differs from the plan


class ReviewWeekRequest(BaseModel):
    week_start: str


@router.get("/review/week")
def review_week_get(week_start: str):
    from src.utils.week_review import review_week
    return review_week(week_start)


@router.post("/review/match")
def review_match(req: MatchRequest):
    from src.utils.week_review import apply_match
    try:
        apply_match(req.workout_id, req.proposed_workout_id, req.label, note=req.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


@router.post("/review/confirm-all")
def review_confirm_all(req: ReviewWeekRequest):
    """Accept every pending suggestion that has a concrete match or label."""
    from src.utils.week_review import apply_match, review_week
    confirmed = 0
    for row in review_week(req.week_start)["workouts"]:
        m = row["match"] or {}
        if row["status"] != "suggested" or not m.get("name"):
            continue
        apply_match(row["id"], m.get("proposed_workout_id"), None if m.get("proposed_workout_id") else m["name"])
        confirmed += 1
    return {"confirmed": confirmed}


@router.post("/review/sync")
def review_sync(req: ReviewWeekRequest):
    from src.utils.week_review import start_sync
    return start_sync(req.week_start)


@router.get("/review/sync")
def review_sync_status():
    from src.utils.week_review import sync_status
    return sync_status()


@router.post("/review/link")
def review_link(req: ReviewWeekRequest):
    """After manual uploads: attach ride files to workouts and refresh derived data."""
    from src.storage.workout_matching import link_fit_files
    monday = _monday(req.week_start)
    sunday = (datetime.strptime(monday, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
    db = WorkoutDatabase()
    linked = link_fit_files(db.db_path, monday, sunday)
    training_load.refresh_all(db.db_path)
    return {"linked": linked}


# ── Weather for the calendar ─────────────────────────────────────────────────

_weather_cache: Dict[str, Any] = {}
WEATHER_TTL_SECONDS = 30 * 60


def _fetch_forecast(lat: float, lon: float) -> Dict[str, Any]:
    import requests
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "timezone": "America/Los_Angeles",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "temperature_unit": "fahrenheit", "past_days": 7, "forecast_days": 14},
        timeout=6)
    r.raise_for_status()
    return r.json()


@router.get("/weather")
def weather(start: str, end: str):
    """Daily forecast for [start, end] at the configured spot (WEATHER_LAT / WEATHER_LON, default Portland, OR).

    The forecast service only sees a city-level coordinate. Results are cached, and any failure
    returns an empty set so the calendar simply shows no chips.
    """
    import time
    lat = float(os.getenv("WEATHER_LAT", "45.52"))
    lon = float(os.getenv("WEATHER_LON", "-122.68"))
    key = f"{lat:.2f},{lon:.2f}"
    hit = _weather_cache.get(key)
    if not hit or time.time() - hit["at"] > WEATHER_TTL_SECONDS:
        try:
            data = _fetch_forecast(lat, lon)["daily"]
            days = {d: {"code": c, "high": hi, "low": lo, "rain_pct": p}
                    for d, c, hi, lo, p in zip(data["time"], data["weather_code"], data["temperature_2m_max"],
                                               data["temperature_2m_min"], data["precipitation_probability_max"])}
            hit = _weather_cache[key] = {"at": time.time(), "days": days}
        except Exception:
            return {"days": {}}
    return {"days": {d: v for d, v in hit["days"].items() if start <= d <= end}}
