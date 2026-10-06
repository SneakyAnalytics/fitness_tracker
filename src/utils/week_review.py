"""Weekly review: suggest how each completed workout maps to the plan, then confirm.

Deterministic (no LLM): the same-day planned workout of the same sport, with
Zwift's title and duration as tie-breakers, or an unplanned category
(commute, sauna...) for everything outside the plan. The athlete confirms with
one tap; confirmed matches are authoritative everywhere (analysis, coach).
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.config import get_db_path

UNPLANNED_CATEGORIES = ["Commute to work", "Commute from work", "Sauna", "Walk / hike", "Other ride", "Other"]

# Completed-workout type (TrainingPeaks) -> planned types it can fulfil.
_SPORTS = {
    "bike": {"bike"},
    "run": {"run"},
    "strength": {"strength"},
    "yoga": {"mobility", "yoga", "other"},
    "other": {"other", "mobility", "yoga"},
    "walk": {"other", "walk"},
    "xc-ski": {"other"},
}

HIGH, MEDIUM = 90, 60
UNPLANNED_ANALYSIS_MIN_MINUTES = 60


def _norm(text: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (text or "").lower()).strip()


def _pacific_hour(start_time: Optional[str]) -> Optional[int]:
    if not start_time:
        return None
    try:
        import pytz
        t = datetime.fromisoformat(start_time)
        if t.tzinfo is None:
            t = pytz.UTC.localize(t)
        return t.astimezone(pytz.timezone("America/Los_Angeles")).hour
    except (ValueError, ImportError):
        return None


def _score(workout: Dict[str, Any], plan: Dict[str, Any]) -> float:
    wtype = (workout["type"] or "").lower()
    ptype = (plan["type"] or "").lower()
    title, name = _norm(workout["title"]), _norm(plan["name"])
    title_hit = bool(name) and name[:20] in title  # Zwift titles carry the workout name
    if ptype not in _SPORTS.get(wtype, {wtype}) and not title_hit:
        return 0.0
    score = 40.0 + (60.0 if title_hit else 0.0)
    if workout["date"] == plan["date"]:
        score += 20
    else:
        score -= 15 * abs((datetime.strptime(workout["date"], "%Y-%m-%d")
                           - datetime.strptime(plan["date"], "%Y-%m-%d")).days)
    planned = plan.get("planned_minutes") or 0
    if planned and workout["minutes"]:
        score += 30 * max(0.0, 1 - abs(workout["minutes"] - planned) / planned)
    return score


def _unplanned_guess(workout: Dict[str, Any], same_day_commutes: List[Dict[str, Any]]) -> Optional[str]:
    wtype = (workout["type"] or "").lower()
    title = (workout["title"] or "").lower()
    if "sauna" in title:
        return "Sauna"
    if wtype in ("walk",) or "hike" in title or "walk" in title:
        return "Walk / hike"
    if wtype == "bike" and not title.startswith("zwift") and workout["minutes"] and workout["minutes"] <= 75:
        weekday = datetime.strptime(workout["date"], "%Y-%m-%d").weekday() < 5
        if weekday:
            hour = workout.get("start_hour")
            if hour is not None:
                return "Commute to work" if hour < 12 else "Commute from work"
            # No clock time: the earlier of two same-day commutes is "to work".
            ids = sorted(w["id"] for w in same_day_commutes)
            return "Commute to work" if ids and workout["id"] == ids[0] else "Commute from work"
        return "Other ride"
    if wtype == "bike":
        return "Other ride"
    return None


def _week_rows(conn: sqlite3.Connection, start: str, end: str):
    workouts = []
    for r in conn.execute("""
        SELECT w.id, w.workout_day, w.workout_title, w.workout_data, w.proposed_workout_id,
               w.proposed_workout_name, w.match_source, w.fit_file_id,
               json_extract(f.fit_data, '$.start_time'), wa.execution_score, wa.proposed_workout_id
        FROM workouts w
        LEFT JOIN fit_files f ON f.id = w.fit_file_id
        LEFT JOIN workout_analyses wa ON wa.workout_id = w.id
        WHERE w.workout_day BETWEEN ? AND ? ORDER BY w.workout_day, w.id""", (start, end)):
        data = json.loads(r[3] or "{}") or {}
        metrics = data.get("metrics") or {}
        workouts.append({
            "id": r[0], "date": r[1][:10], "title": r[2], "type": data.get("type"),
            "minutes": round(metrics.get("actual_duration") or 0), "tss": metrics.get("actual_tss"),
            "proposed_workout_id": r[4], "label": r[5], "match_source": r[6], "has_fit": bool(r[7]),
            "start_hour": _pacific_hour(r[8]), "execution_score": r[9], "analysis_plan_id": r[10],
        })
    plans = [{"id": r[0], "date": r[1], "type": r[2], "name": r[3], "planned_minutes": r[4],
              "tss_min": r[5], "tss_max": r[6]} for r in conn.execute("""
        SELECT pw.id, dp.date, pw.type, pw.name, pw.plannedDuration, pw.plannedTSS_min, pw.plannedTSS_max
        FROM proposed_workouts pw JOIN daily_plans dp ON dp.id = pw.dailyPlanId
        WHERE dp.date BETWEEN ? AND ? AND pw.type != 'rest' ORDER BY dp.date, pw.id""", (start, end))]
    return workouts, plans


def review_week(week_start: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    start = datetime.strptime(week_start[:10], "%Y-%m-%d").date()
    start -= timedelta(days=start.weekday())
    end = start + timedelta(days=6)
    conn = sqlite3.connect(db_path or get_db_path())
    try:
        workouts, plans = _week_rows(conn, start.isoformat(), end.isoformat())
    finally:
        conn.close()

    plans_by_id = {p["id"]: p for p in plans}
    confirmed = [w for w in workouts if w["match_source"] == "manual"]
    taken = {w["proposed_workout_id"] for w in confirmed if w["proposed_workout_id"]}

    # One-to-one greedy assignment of the best-scoring (workout, plan) pairs.
    open_workouts = [w for w in workouts if w["match_source"] != "manual"]
    pairs = sorted(((s, w["id"], p["id"]) for w in open_workouts for p in plans
                    if p["id"] not in taken and (s := _score(w, p)) >= MEDIUM), reverse=True)
    suggestion: Dict[int, Dict[str, Any]] = {}
    for s, wid, pid in pairs:
        if wid in suggestion or pid in taken:
            continue
        taken.add(pid)
        suggestion[wid] = {"kind": "plan", "proposed_workout_id": pid, "name": plans_by_id[pid]["name"],
                           "confidence": "high" if s >= HIGH else "medium"}

    rows = []
    for w in workouts:
        if w["match_source"] == "manual":
            status = "confirmed"
            match = ({"kind": "plan", "proposed_workout_id": w["proposed_workout_id"],
                      "name": plans_by_id.get(w["proposed_workout_id"], {}).get("name") or w["label"]}
                     if w["proposed_workout_id"] else {"kind": "unplanned", "name": w["label"]})
        else:
            status = "suggested"
            match = suggestion.get(w["id"])
            if not match:
                commutes = [x for x in workouts if x["date"] == w["date"] and (x["type"] or "").lower() == "bike"
                            and not (x["title"] or "").lower().startswith("zwift")]
                guess = _unplanned_guess(w, commutes)
                match = {"kind": "unplanned", "name": guess, "confidence": "medium" if guess else "low"}
        rows.append({**{k: w[k] for k in ("id", "date", "title", "type", "minutes", "tss", "has_fit",
                                          "execution_score")},
                     "status": status, "match": match, "analysis": analysis_status(w["id"])})

    matched_plan_ids = {r["match"].get("proposed_workout_id") for r in rows if r["status"] == "confirmed"}
    return {
        "week_start": start.isoformat(),
        "workouts": rows,
        "planned": [{**p, "done": p["id"] in matched_plan_ids} for p in plans],
        "categories": UNPLANNED_CATEGORIES,
        "sync": sync_status(),
    }


# ── Applying matches (+ background analysis) ────────────────────────────────

def apply_match(workout_id: int, proposed_workout_id: Optional[int] = None, label: Optional[str] = None,
                db_path: Optional[str] = None) -> None:
    from src.storage.workout_matching import match_workout_to_proposed
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    try:
        if proposed_workout_id:
            row = conn.execute("SELECT name FROM proposed_workouts WHERE id = ?", (proposed_workout_id,)).fetchone()
            if not row:
                raise ValueError(f"planned workout {proposed_workout_id} not found")
            name = row[0]
        else:
            name = (label or "").strip()
            if not name:
                raise ValueError("choose a planned workout or give a label")
        prev = conn.execute(
            "SELECT w.fit_file_id, wa.id, wa.proposed_workout_id,"
            " json_extract(w.workout_data, '$.metrics.actual_duration') FROM workouts w "
            "LEFT JOIN workout_analyses wa ON wa.workout_id = w.id WHERE w.id = ?", (workout_id,)).fetchone()
    finally:
        conn.close()
    if prev is None:
        raise ValueError(f"workout {workout_id} not found")
    match_workout_to_proposed(path, workout_id, name, "manual", proposed_workout_id=proposed_workout_id)
    has_fit, has_analysis, analysed_against, minutes = prev
    # Planned workouts get analyzed against their plan; unplanned sessions only
    # when substantial (commutes and sauna don't need an AI write-up).
    worth_it = bool(proposed_workout_id) or (minutes or 0) >= UNPLANNED_ANALYSIS_MIN_MINUTES
    # Re-analyze only when the comparison target changed (or there's no analysis yet).
    if has_fit and worth_it and (not has_analysis or analysed_against != proposed_workout_id):
        queue_analysis(workout_id, path)


_jobs: Dict[int, Dict[str, Any]] = {}
_queue: deque = deque()
_lock = threading.Lock()
_worker: Optional[threading.Thread] = None


def analysis_status(workout_id: int) -> Optional[Dict[str, Any]]:
    return _jobs.get(workout_id)


def queue_analysis(workout_id: int, db_path: str) -> None:
    global _worker
    with _lock:
        if _jobs.get(workout_id, {}).get("state") in ("queued", "running"):
            return
        _jobs[workout_id] = {"state": "queued"}
        _queue.append((workout_id, db_path))
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_drain, daemon=True)
            _worker.start()


def _drain() -> None:
    from src.storage.database import WorkoutDatabase
    from src.storage.events import record_event
    from src.utils.reanalyze import reanalyze_workout
    while True:
        with _lock:
            if not _queue:
                return
            workout_id, db_path = _queue.popleft()
            _jobs[workout_id] = {"state": "running"}
        try:
            result = reanalyze_workout(workout_id, WorkoutDatabase(db_path))
            score = ((result or {}).get("execution") or {}).get("execution_score")
            _jobs[workout_id] = {"state": "done", "execution_score": score}
        except Exception as exc:  # keep the queue alive; surface the failure
            _jobs[workout_id] = {"state": "error", "message": str(exc)}
            record_event("error", "week_review", f"Analysis failed for workout {workout_id}: {exc}", db_path=db_path)


# ── TrainingPeaks sync job ──────────────────────────────────────────────────

_sync: Dict[str, Any] = {"state": "idle"}


def sync_status() -> Dict[str, Any]:
    return dict(_sync)


def start_sync(week_start: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    if _sync.get("state") == "running":
        return sync_status()
    start = datetime.strptime(week_start[:10], "%Y-%m-%d").date()
    start -= timedelta(days=start.weekday())
    end = min(start + timedelta(days=6), datetime.now().date())
    _sync.clear()
    _sync.update(state="running", started=datetime.now().isoformat(timespec="seconds"),
                 range=[start.isoformat(), end.isoformat()])

    def run():
        from src.storage.events import record_event
        from src.storage.workout_matching import link_fit_files
        from src.utils.trainingpeaks_sync import TrainingPeaksSync
        from src.utils.training_load import refresh_all
        try:
            results = TrainingPeaksSync().run_sync(start, end)
            if not results:
                raise RuntimeError("TrainingPeaks sync failed (see API logs)")
            path = db_path or get_db_path()
            linked = link_fit_files(path, start.isoformat(), end.isoformat())
            refresh_all(path)
            _sync.update(state="done", finished=datetime.now().isoformat(timespec="seconds"),
                         message=f"{results.get('fit_files', 0)} ride files, workouts "
                                 f"{'updated' if results.get('workouts') else 'unchanged'}, {linked} linked",
                         errors=results.get("errors") or [])
        except Exception as exc:
            _sync.update(state="error", finished=datetime.now().isoformat(timespec="seconds"), message=str(exc))
            record_event("error", "trainingpeaks_sync", f"Sync from the app failed: {exc}", db_path=db_path)

    threading.Thread(target=run, daemon=True).start()
    return sync_status()
