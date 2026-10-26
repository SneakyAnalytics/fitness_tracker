"""Endpoints for the Compare page: pick rides, overlay their power and heart rate."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from src.storage.database import WorkoutDatabase
from src.utils.ride_compare import ride_series

router = APIRouter(prefix="/compare")


def _rows(sql: str, args=()) -> list:
    conn = sqlite3.connect(WorkoutDatabase().db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


@router.get("/rides")
def rides(limit: int = 120):
    """Recent workouts that have a ride file, newest first, named for the plan when matched."""
    rows = _rows(
        "SELECT w.id, w.workout_day AS day, w.workout_title AS title, pw.name AS plan_name,"
        " json_extract(w.workout_data, '$.metrics.actual_tss') AS tss,"
        " json_extract(w.workout_data, '$.metrics.actual_duration') AS minutes"
        " FROM workouts w LEFT JOIN proposed_workouts pw ON pw.id = w.proposed_workout_id"
        " WHERE w.fit_file_id IS NOT NULL ORDER BY w.workout_day DESC, w.id DESC LIMIT ?",
        (min(max(limit, 1), 400),))
    return {"rides": [{"id": r["id"], "date": r["day"], "name": r["plan_name"] or r["title"],
                       "tss": r["tss"], "minutes": r["minutes"]} for r in rows]}


@router.get("/rides/{workout_id}")
def ride(workout_id: int, step: int = 10, smooth: int = 30):
    row = _rows(
        "SELECT w.id, w.workout_day AS day, w.workout_title AS title, pw.name AS plan_name, f.fit_data"
        " FROM workouts w LEFT JOIN proposed_workouts pw ON pw.id = w.proposed_workout_id"
        " LEFT JOIN fit_files f ON f.id = w.fit_file_id WHERE w.id = ?", (workout_id,))
    if not row:
        raise HTTPException(status_code=404, detail="workout not found")
    row = row[0]
    if not row["fit_data"]:
        raise HTTPException(status_code=404, detail="this workout has no ride file")
    data: Dict[str, Any] = ride_series(json.loads(row["fit_data"]), step=min(max(step, 1), 60),
                                       smooth_window=min(max(smooth, 1), 300))
    intervals = _rows(
        "SELECT interval_index, name, label, duration_sec, target_low_w, target_high_w, actual_avg_w, compliance"
        " FROM interval_results WHERE workout_id = ? ORDER BY interval_index", (workout_id,))
    return {"id": row["id"], "date": row["day"], "name": row["plan_name"] or row["title"], **data,
            "intervals": [dict(i) for i in intervals]}
