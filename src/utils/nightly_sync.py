"""Nightly job: pull recent workouts from TrainingPeaks, link ride files, analyze.

Run by the Beelink task FitnessTrackerNightlySync (scripts/beelink_nightly_sync.ps1):
  python -m src.utils.nightly_sync [--days 3] [--no-sync]

Matching here is only a suggestion (the same one the Review step shows); nothing
is marked confirmed, so the Sunday review still decides. Planned workouts are
analyzed against their suggested plan; short unplanned sessions are skipped.
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import date, timedelta
from typing import Any, Dict, List

from src.storage.database import WorkoutDatabase
from src.storage.events import record_event
from src.storage.workout_matching import link_fit_files
from src.utils.training_load import refresh_all
from src.utils.week_review import UNPLANNED_ANALYSIS_MIN_MINUTES, review_week


def _unanalyzed(db_path: str, start: str, end: str) -> List[int]:
    conn = sqlite3.connect(db_path)
    try:
        return [r[0] for r in conn.execute(
            "SELECT w.id FROM workouts w LEFT JOIN workout_analyses wa ON wa.workout_id = w.id "
            "WHERE w.workout_day BETWEEN ? AND ? AND w.fit_file_id IS NOT NULL AND wa.id IS NULL "
            "ORDER BY w.workout_day, w.id", (start, end))]
    finally:
        conn.close()


def run(days: int = 3, sync: bool = True) -> Dict[str, Any]:
    db = WorkoutDatabase()
    end = date.today()
    start = end - timedelta(days=days - 1)
    result: Dict[str, Any] = {"range": [start.isoformat(), end.isoformat()], "errors": []}

    if sync:
        from src.utils.trainingpeaks_sync import TrainingPeaksSync
        synced = TrainingPeaksSync().run_sync(start, end)
        if not synced:
            result["errors"].append("TrainingPeaks sync failed (see container logs)")
        else:
            result["synced"] = {k: synced.get(k) for k in ("fit_files", "workouts", "metrics")}

    result["linked"] = link_fit_files(db.db_path, start.isoformat(), end.isoformat())

    # Suggestions for every week the range touches.
    suggestions: Dict[int, Dict[str, Any]] = {}
    monday = start - timedelta(days=start.weekday())
    while monday <= end:
        for row in review_week(monday.isoformat(), db.db_path)["workouts"]:
            suggestions[row["id"]] = row
        monday += timedelta(days=7)

    from src.utils.fit_file_analyzer import FitFileAnalyzer
    from src.utils.reanalyze import reanalyze_workout
    analyzer = None
    analyzed = 0
    for wid in _unanalyzed(db.db_path, start.isoformat(), end.isoformat()):
        row = suggestions.get(wid, {})
        match = row.get("match") or {}
        plan_id = match.get("proposed_workout_id") if row.get("status") == "suggested" else None
        if not plan_id and row.get("status") != "confirmed" and (row.get("minutes") or 0) < UNPLANNED_ANALYSIS_MIN_MINUTES:
            continue  # short unplanned session (commute, sauna): no write-up needed
        try:
            analyzer = analyzer or FitFileAnalyzer(use_dynamic_models=True)
            if reanalyze_workout(wid, db, analyzer, suggested_plan_id=plan_id):
                analyzed += 1
        except Exception as exc:  # one bad file mustn't stop the rest
            result["errors"].append(f"analysis of workout {wid} failed: {exc}")
    result["analyzed"] = analyzed

    refresh_all(db.db_path)
    if result["errors"]:
        record_event("error", "nightly_sync", f"{len(result['errors'])} problem(s) in the nightly sync",
                     result["errors"], db_path=db.db_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=3, help="how many days back to sync (default 3)")
    parser.add_argument("--no-sync", action="store_true", help="skip TrainingPeaks; link and analyze only")
    args = parser.parse_args()
    result = run(args.days, sync=not args.no_sync)
    print(result)
    raise SystemExit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
