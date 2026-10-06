"""Tools the weekly coach can call to look things up instead of asking again.

Each tool is a small, read-mostly function over data that already exists. The
definitions below are passed to Claude; `run_tool` executes a call and returns
compact JSON. The only writes are to goals, so the coach can record an event
the athlete mentions the moment they mention it.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from src.config import get_db_path
from src.storage import goals as goals_store
from src.utils import progression, training_load

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_training_load",
        "description": ("Weekly TSS and end-of-week fitness (CTL) for a date range, plus current CTL/ATL/TSB. "
                        "Use to judge how load has trended and whether the athlete is building, holding or slipping."),
        "input_schema": {"type": "object", "properties": {
            "start_date": {"type": "string", "description": "YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "YYYY-MM-DD"}},
            "required": ["start_date", "end_date"], "additionalProperties": False},
    },
    {
        "name": "get_progression",
        "description": ("Recent sessions of one workout type with the work actually done (structure, average work "
                        "power, %FTP, minutes of work, execution score). Use before prescribing a key session so "
                        "the next one is a deliberate step up from the last."),
        "input_schema": {"type": "object", "properties": {
            "archetype": {"type": "string", "enum": list(progression.ARCHETYPES)},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20}},
            "required": ["archetype"], "additionalProperties": False},
    },
    {
        "name": "compare_to_period",
        "description": ("Compare fitness now with N weeks ago: CTL then vs now and best power at 5s/1m/5m/20m/60m "
                        "over matching windows. Answers 'am I fitter than last year/last block?'."),
        "input_schema": {"type": "object", "properties": {
            "weeks_ago": {"type": "integer", "minimum": 1, "maximum": 156},
            "window_days": {"type": "integer", "minimum": 14, "maximum": 180}},
            "required": ["weeks_ago"], "additionalProperties": False},
    },
    {
        "name": "get_readiness",
        "description": ("HRV, resting HR, sleep and Body Battery for the last 7 days vs a 60-day baseline, with "
                        "flags. Check before adding load or when the athlete reports fatigue."),
        "input_schema": {"type": "object", "properties": {
            "as_of": {"type": "string", "description": "YYYY-MM-DD, defaults to today"}},
            "additionalProperties": False},
    },
    {
        "name": "search_prior_conversations",
        "description": ("Full-text search across every past weekly coaching conversation. ALWAYS search before "
                        "asking the athlete about schedule constraints, equipment, injuries, events or "
                        "preferences: they may have told you already."),
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string", "description": "words to look for, e.g. 'knee' or 'travel October'"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20}},
            "required": ["query"], "additionalProperties": False},
    },
    {
        "name": "get_goals",
        "description": "The athlete's goals and events with priority, target date and days until it.",
        "input_schema": {"type": "object", "properties": {
            "include_inactive": {"type": "boolean"}}, "additionalProperties": False},
    },
    {
        "name": "save_goal",
        "description": ("Record a NEW goal or event the athlete just mentioned (only things they explicitly "
                        "stated). Priority 1 = A event that drives tapers, 2 = B, 3+ = background goal."),
        "input_schema": {"type": "object", "properties": {
            "description": {"type": "string"},
            "category": {"type": "string", "enum": ["event", "power", "endurance", "technical", "consistency", "body"]},
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            "target_date": {"type": "string", "description": "YYYY-MM-DD if known"},
            "note": {"type": "string"}},
            "required": ["description", "category", "priority"], "additionalProperties": False},
    },
    {
        "name": "update_goal",
        "description": ("Update an existing goal: mark completed/paused/abandoned, change its date or priority, "
                        "or append a progress note. Use the id from get_goals."),
        "input_schema": {"type": "object", "properties": {
            "goal_id": {"type": "integer"},
            "status": {"type": "string", "enum": list(goals_store.VALID_STATUSES)},
            "target_date": {"type": "string"},
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            "note": {"type": "string"}},
            "required": ["goal_id"], "additionalProperties": False},
    },
    {
        "name": "get_week_detail",
        "description": ("Everything about one past or current week: the plan, what was actually done each day "
                        "(matched to the plan or not), execution scores, athlete comments and analysis excerpts."),
        "input_schema": {"type": "object", "properties": {
            "week_start": {"type": "string", "description": "Monday, YYYY-MM-DD"}},
            "required": ["week_start"], "additionalProperties": False},
    },
    {
        "name": "get_workout_intervals",
        "description": "Per-interval prescribed vs actual power for one completed workout id.",
        "input_schema": {"type": "object", "properties": {
            "workout_id": {"type": "integer"}}, "required": ["workout_id"], "additionalProperties": False},
    },
]


def _conn(db_path: Optional[str]) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _parse(d: Optional[str], default: date) -> date:
    return datetime.strptime(d[:10], "%Y-%m-%d").date() if d else default


def _get_training_load(args, db_path):
    start, end = _parse(args["start_date"], date.today()), _parse(args["end_date"], date.today())
    weeks = training_load.weekly_load(db_path, weeks=max(1, (end - start).days // 7 + 1), end=end + timedelta(days=1))
    return {"weeks": [w for w in weeks if w["week_start"] >= (start - timedelta(days=start.weekday())).isoformat()],
            "now": training_load.load_snapshot(db_path, as_of=end)}


def _get_progression(args, db_path):
    return {"archetype": args["archetype"],
            "sessions": progression.get_progression(args["archetype"], args.get("limit", 8), db_path)}


def _compare_to_period(args, db_path):
    today = date.today()
    then = today - timedelta(weeks=args["weeks_ago"])
    window = args.get("window_days", 60)
    now_curve = training_load.power_curve((today - timedelta(days=window)).isoformat(), today.isoformat(), db_path)
    then_curve = training_load.power_curve((then - timedelta(days=window)).isoformat(), then.isoformat(), db_path)
    return {"now": {"date": today.isoformat(), **training_load.load_snapshot(db_path, as_of=today),
                    "best_power": now_curve},
            "then": {"date": then.isoformat(), **training_load.load_snapshot(db_path, as_of=then),
                     "best_power": then_curve},
            "note": "best_power rides=0 means no FIT power data for that window (FIT archive starts late 2025)."}


def _get_readiness(args, db_path):
    return training_load.readiness(_parse(args.get("as_of"), date.today()), db_path)


def _search_prior_conversations(args, db_path):
    terms = [t.lower() for t in args["query"].split() if len(t) > 2] or [args["query"].lower()]
    limit = args.get("limit", 8)
    conn = _conn(db_path)
    try:
        sessions = conn.execute(
            "SELECT week_start_date, messages FROM coach_chat_sessions ORDER BY week_start_date DESC").fetchall()
    finally:
        conn.close()
    hits = []
    for s in sessions:
        try:
            messages = json.loads(s["messages"] or "[]")
        except ValueError:
            continue
        for m in messages:
            text = m.get("content") or ""
            lowered = text.lower()
            score = sum(lowered.count(t) for t in terms)
            if not score:
                continue
            pos = min((lowered.find(t) for t in terms if t in lowered), default=0)
            snippet = text[max(0, pos - 250): pos + 450].strip()
            hits.append({"week_start": s["week_start_date"], "speaker": m.get("role"), "score": score,
                         "excerpt": snippet})
    hits.sort(key=lambda h: (h["score"], h["week_start"]), reverse=True)  # best match, newest first
    return {"query": args["query"], "matches": hits[:limit], "sessions_searched": len(sessions)}


def _get_goals(args, db_path):
    return {"goals": goals_store.list_goals(args.get("include_inactive", False), db_path)}


def _save_goal(args, db_path):
    return {"saved": goals_store.add_goal(args["description"], args.get("category", "event"),
                                          args.get("priority", 3), args.get("target_date"), args.get("note"),
                                          db_path)}


def _update_goal(args, db_path):
    updated = goals_store.update_goal(args["goal_id"], args.get("status"), args.get("target_date"),
                                      args.get("priority"), args.get("note"), db_path)
    return {"updated": updated} if updated else {"error": f"no goal with id {args['goal_id']}"}


def _get_week_detail(args, db_path):
    start = _parse(args["week_start"], date.today())
    start -= timedelta(days=start.weekday())
    end = start + timedelta(days=6)
    conn = _conn(db_path)
    try:
        plan = conn.execute("SELECT weekNumber, startDate, plannedTSS_min, plannedTSS_max, ftp, rationale "
                            "FROM weekly_plans WHERE startDate = ?", (start.isoformat(),)).fetchone()
        planned = conn.execute(
            "SELECT pw.id, dp.date, pw.type, pw.name, pw.plannedDuration, pw.plannedTSS_min, pw.plannedTSS_max "
            "FROM proposed_workouts pw JOIN daily_plans dp ON dp.id = pw.dailyPlanId "
            "WHERE dp.date BETWEEN ? AND ? ORDER BY dp.date, pw.id", (start.isoformat(), end.isoformat())).fetchall()
        done = conn.execute(
            "SELECT w.id, w.workout_day, w.workout_title, w.proposed_workout_id, w.proposed_workout_name, "
            "json_extract(w.workout_data, '$.type') AS type, json_extract(w.workout_data, '$.metrics.actual_tss') AS tss, "
            "json_extract(w.workout_data, '$.metrics.actual_duration') AS minutes, w.athlete_comments, "
            "wa.execution_score, substr(wa.analysis_text, 1, 600) AS analysis_excerpt "
            "FROM workouts w LEFT JOIN workout_analyses wa ON wa.workout_id = w.id "
            "WHERE w.workout_day BETWEEN ? AND ? ORDER BY w.workout_day, w.id",
            (start.isoformat(), end.isoformat())).fetchall()
    finally:
        conn.close()
    return {"week_start": start.isoformat(), "plan": dict(plan) if plan else None,
            "planned": [dict(r) for r in planned], "completed": [dict(r) for r in done]}


def _get_workout_intervals(args, db_path):
    conn = _conn(db_path)
    try:
        rows = conn.execute(
            "SELECT interval_index, name, label, duration_sec, target_low_w, target_high_w, actual_avg_w, "
            "deviation_pct, compliance FROM interval_results WHERE workout_id = ? ORDER BY interval_index",
            (args["workout_id"],)).fetchall()
    finally:
        conn.close()
    return {"workout_id": args["workout_id"], "intervals": [dict(r) for r in rows]}


_HANDLERS: Dict[str, Callable[[Dict[str, Any], Optional[str]], Any]] = {
    "get_training_load": _get_training_load,
    "get_progression": _get_progression,
    "compare_to_period": _compare_to_period,
    "get_readiness": _get_readiness,
    "search_prior_conversations": _search_prior_conversations,
    "get_goals": _get_goals,
    "save_goal": _save_goal,
    "update_goal": _update_goal,
    "get_week_detail": _get_week_detail,
    "get_workout_intervals": _get_workout_intervals,
}

TOOL_STATUS = {
    "get_training_load": "checking training load",
    "get_progression": "reviewing past sessions",
    "compare_to_period": "comparing with earlier fitness",
    "get_readiness": "checking HRV and sleep",
    "search_prior_conversations": "searching past conversations",
    "get_goals": "checking goals",
    "save_goal": "saving goal",
    "update_goal": "updating goal",
    "get_week_detail": "looking at that week",
    "get_workout_intervals": "looking at interval data",
}


def run_tool(name: str, args: Dict[str, Any], db_path: Optional[str] = None) -> str:
    """Execute a tool call; errors come back as data so the model can recover."""
    handler = _HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"unknown tool {name}"})
    try:
        return json.dumps(handler(args or {}, db_path), default=str)
    except (ValueError, KeyError, sqlite3.Error) as exc:
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})


MAX_TOOL_ROUNDS = 8


def stream_tool_conversation(api, extra: Dict[str, Any], model: str, system_text: str,
                             messages: List[Dict[str, Any]], db_path: Optional[str] = None,
                             on_usage: Optional[Callable[[Any], Any]] = None,
                             max_tokens: int = 16000, result: Optional[Dict[str, Any]] = None):
    """Run a Claude turn with tools, yielding ("text", chunk) and ("status", label).

    The model's own words (without status labels) end up in result["text"].
    `messages` is extended in place with the assistant/tool_result turns.
    """
    system = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    rounds: List[str] = []
    for _ in range(MAX_TOOL_ROUNDS):
        round_text = ""
        if rounds and rounds[-1]:
            yield ("text", "\n\n")
        with api.stream(model=model, max_tokens=max_tokens, system=system, tools=TOOLS,
                        messages=messages, cache_control={"type": "ephemeral"}, **extra) as stream:
            for chunk in stream.text_stream:
                round_text += chunk
                yield ("text", chunk)
            final = stream.get_final_message()
        rounds.append(round_text)
        if on_usage:
            on_usage(final.usage)
        if final.stop_reason == "refusal":
            rounds.append("(The model declined to answer that.)")
            break
        if final.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": final.content})
        results = []
        for block in final.content:
            if block.type == "tool_use":
                yield ("status", TOOL_STATUS.get(block.name, block.name))
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": run_tool(block.name, block.input, db_path)})
        messages.append({"role": "user", "content": results})
    if result is not None:
        result["text"] = "\n\n".join(t.strip() for t in rounds if t.strip())
