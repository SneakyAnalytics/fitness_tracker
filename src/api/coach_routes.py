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
from src.utils import progression, training_load
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


@router.post("/coach/session/save")
def save_plan(req: WeekRequest):
    s = _session(req.week_start, req.model)
    zwift_dir = os.getenv("ZWIFT_WORKOUTS_DIR", "shareable/zwift_workouts")
    ok, message, files = s.save_plan(zwift_dir)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message, "zwift_files": files, **_session_state(s)}


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

@router.get("/dashboard/trends")
def dashboard_trends(weeks: int = 16):
    db = WorkoutDatabase()
    ftp = (db.get_athlete_settings() or {}).get("ftp")
    return {
        "load": training_load.load_snapshot(db.db_path),
        "weekly": training_load.weekly_load(db.db_path, weeks=weeks),
        "power_curve": training_load.compare_power_curves(90, db_path=db.db_path),
        "ftp": training_load.ftp_check(ftp, db.db_path),
        "readiness": training_load.readiness(db_path=db.db_path),
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
    return {"workout_id": workout_id, "intervals": [dict(r) for r in rows]}
