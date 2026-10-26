"""Maintenance endpoints behind the React Admin page.

These replace the actions that used to live only in the old Streamlit admin app (last seen at the
`streamlit-final` git tag): the
problems list, deleting a workout, moving a ride file between workouts, and
managing goals.
"""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.storage import goals as goals_store
from src.storage import workout_matching as wm
from src.storage.database import WorkoutDatabase
from src.storage.events import acknowledge_events, unacknowledged_events
from src.utils import training_load

router = APIRouter(prefix="/admin")


def _db_path() -> str:
    return WorkoutDatabase().db_path


def _refresh_after_change() -> None:
    """Ride links and workouts feed CTL, progression and FTP, so rebuild them."""
    training_load.refresh_all(_db_path())


# ── Problems and updates ─────────────────────────────────────────────────────

class DismissRequest(BaseModel):
    ids: List[int] = Field(default_factory=list)


@router.get("/events")
def events(limit: int = 50):
    return {"events": unacknowledged_events(limit=min(max(limit, 1), 200))}


@router.post("/events/dismiss")
def dismiss_events(req: DismissRequest):
    acknowledge_events(req.ids, _db_path())
    return {"dismissed": len(req.ids)}


# ── Workouts and ride files ──────────────────────────────────────────────────

@router.get("/workouts")
def list_workouts(start_date: str, end_date: str):
    """Workouts in a date range with the ride file each one currently holds."""
    return {"workouts": wm.get_workouts_with_fit_files(_db_path(), start_date, end_date)}


@router.get("/fit-files")
def fit_files_for_day(date: str):
    return {"fit_files": wm.get_available_fit_files(_db_path(), date)}


class FitAssignment(BaseModel):
    fit_file_id: Optional[int] = None  # null removes the link


@router.post("/workouts/{workout_id}/fit")
def assign_fit(workout_id: int, req: FitAssignment):
    if not wm.reassign_fit_file(_db_path(), workout_id, req.fit_file_id):
        raise HTTPException(status_code=404, detail="workout not found")
    _refresh_after_change()
    return {"ok": True}


@router.delete("/workouts/{workout_id}")
def remove_workout(workout_id: int):
    if not wm.delete_workout(_db_path(), workout_id):
        raise HTTPException(status_code=404, detail="workout not found")
    _refresh_after_change()
    return {"ok": True}


# ── Goals ────────────────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    category: str = "event"
    priority: int = 3
    target_date: Optional[str] = None
    progress_note: Optional[str] = None


class GoalUpdate(BaseModel):
    status: Optional[str] = None
    target_date: Optional[str] = None
    priority: Optional[int] = None
    progress_note: Optional[str] = None


@router.get("/goals")
def list_goals(include_inactive: bool = True):
    return {"goals": goals_store.list_goals(include_inactive=include_inactive)}


@router.post("/goals")
def create_goal(req: GoalCreate):
    try:
        return goals_store.add_goal(**req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/goals/{goal_id}")
def edit_goal(goal_id: int, req: GoalUpdate):
    try:
        out = goals_store.update_goal(goal_id, **req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if out is None:
        raise HTTPException(status_code=404, detail="goal not found")
    return out
