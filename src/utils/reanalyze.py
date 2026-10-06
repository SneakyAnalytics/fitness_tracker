"""Re-run workout analysis the one correct way.

Every re-analysis (Streamlit buttons, nightly automation, backfills) should go
through `reanalyze_workout` so the athlete's manual match is always honored and
results are persisted identically.

CLI (inside the container):
  python -m src.utils.reanalyze --start 2026-09-01 --end 2026-09-30
  python -m src.utils.reanalyze --workout-id 882
  python -m src.utils.reanalyze --refresh-laps --start 2026-01-01 --end 2026-10-05 --no-ai
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import PROJECT_ROOT
from src.storage.database import WorkoutDatabase
from src.utils.erg_execution import compute_execution

RAW_FIT_DIR = PROJECT_ROOT / "data" / "trainingpeaks_extracted"


def _load_workout(db: WorkoutDatabase, workout_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(db.db_path)
    try:
        row = conn.execute(
            "SELECT w.id, w.workout_day, w.workout_title, w.fit_file_id, w.athlete_comments, f.fit_data "
            "FROM workouts w LEFT JOIN fit_files f ON f.id = w.fit_file_id WHERE w.id = ?",
            (workout_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    fit_data = json.loads(row[5]) if row[5] else None
    return {"id": row[0], "day": row[1], "title": row[2], "fit_file_id": row[3],
            "comments": row[4], "fit_data": fit_data}


def reanalyze_workout(workout_id: int, db: Optional[WorkoutDatabase] = None,
                      analyzer=None, suggested_plan_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Analyze one workout against its manual match and persist the result.

    `suggested_plan_id` is used only when the athlete hasn't confirmed a match
    yet (nightly runs); a confirmed match always wins.
    """
    from src.utils.fit_file_analyzer import FitFileAnalyzer  # heavy import (Gemini SDK)

    db = db or WorkoutDatabase()
    workout = _load_workout(db, workout_id)
    if not workout or not workout["fit_data"]:
        return None
    fit_data = workout["fit_data"]
    fit_data["title"] = workout["title"]
    fit_data["workout_day"] = workout["day"]
    fit_data["workout_date"] = workout["day"]

    match = db.get_workout_match(workout_id)
    if match["match_source"] != "manual" and suggested_plan_id:
        match = {"proposed_workout_id": suggested_plan_id, "proposed_workout_name": None, "match_source": None}
    ftp = (db.get_athlete_settings() or {}).get("ftp")
    analyzer = analyzer or FitFileAnalyzer(use_dynamic_models=True)
    analysis = analyzer.analyze_workout_from_parsed_data(
        parsed_data=fit_data,
        athlete_ftp=float(ftp) if ftp else None,
        athlete_notes=workout["comments"],
        matched_proposed_workout_id=match["proposed_workout_id"],
        matched_proposed_workout_name=None if match["proposed_workout_id"] else match["proposed_workout_name"],
    )
    if analysis:
        db.store_analysis_result(workout_id, workout["fit_file_id"], analysis,
                                 model_used=analyzer.last_model_used)
    return analysis


def find_raw_fit(file_name: str, raw_dir: Path = RAW_FIT_DIR) -> Optional[Path]:
    if not file_name or not raw_dir.exists():
        return None
    matches = sorted(raw_dir.glob(f"*{file_name}"))
    return matches[0] if matches else None


def refresh_laps(fit_file_id: int, db: Optional[WorkoutDatabase] = None,
                 raw_dir: Path = RAW_FIT_DIR) -> bool:
    """Add lap markers (with Zwift ERG targets) to stored fit_data by re-parsing
    the archived raw file.

    Older uploads were parsed before lap extraction existed. Only `laps` is
    replaced; every other stored value is left exactly as it was.
    """
    from src.utils.fit_parser import FitParser

    db = db or WorkoutDatabase()
    conn = sqlite3.connect(db.db_path)
    try:
        row = conn.execute("SELECT file_name, fit_data FROM fit_files WHERE id = ?", (fit_file_id,)).fetchone()
        if not row or not row[1]:
            return False
        stored = json.loads(row[1])
        if not isinstance(stored, dict):
            return False
        laps_now = stored.get("laps") or []
        if laps_now and all("avg_target_power" in lap for lap in laps_now):
            return False  # already has laps including Zwift's ERG targets
        raw = find_raw_fit(row[0], raw_dir)
        if not raw:
            return False
        parsed = FitParser().parse_fit_file(raw.read_bytes())
        laps = (parsed or {}).get("laps") or []
        if not laps:
            return False
        stored["laps"] = laps
        conn.execute("UPDATE fit_files SET fit_data = ? WHERE id = ?", (json.dumps(stored, default=str), fit_file_id))
        conn.commit()
        return True
    finally:
        conn.close()


def recompute_execution_only(workout_id: int, db: Optional[WorkoutDatabase] = None) -> Optional[Dict[str, Any]]:
    """Refresh interval_results and the execution score without calling any LLM."""
    from src.utils.fit_file_analyzer import FitFileAnalyzer

    db = db or WorkoutDatabase()
    workout = _load_workout(db, workout_id)
    match = db.get_workout_match(workout_id)
    if not workout or not workout["fit_data"] or not match["proposed_workout_id"]:
        return None
    analyzer = FitFileAnalyzer.__new__(FitFileAnalyzer)  # lookups only; no Gemini client needed
    proposed = analyzer._load_proposed_workout_by_id(match["proposed_workout_id"])
    if not proposed or not proposed.get("intervals"):
        return None
    ftp = (db.get_athlete_settings() or {}).get("ftp")
    execution = compute_execution(proposed, workout["fit_data"],
                                  FitFileAnalyzer._prescription_ftp(proposed, workout["fit_data"], ftp))
    if not execution:
        return None
    conn = sqlite3.connect(db.db_path)
    try:
        conn.execute("DELETE FROM interval_results WHERE workout_id = ?", (workout_id,))
        for r in execution["intervals"]:
            conn.execute(
                "INSERT INTO interval_results (workout_id, proposed_workout_id, interval_index, name, label,"
                " duration_sec, target_low_w, target_high_w, actual_avg_w, deviation_pct, compliance, alignment)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (workout_id, proposed["id"], r["index"], r["name"], r["label"], r["duration_sec"],
                 r["target_low_w"], r["target_high_w"], r["actual_avg_w"], r["deviation_pct"],
                 r["compliance"], execution["alignment"]),
            )
        conn.execute(
            "UPDATE workout_analyses SET execution_score = ?, proposed_workout_id = ? WHERE workout_id = ?",
            (execution["execution_score"], proposed["id"], workout_id),
        )
        conn.commit()
    finally:
        conn.close()
    return execution


def _workout_ids(db: WorkoutDatabase, start: str, end: str) -> List[int]:
    conn = sqlite3.connect(db.db_path)
    try:
        rows = conn.execute(
            "SELECT id FROM workouts WHERE workout_day BETWEEN ? AND ? AND fit_file_id IS NOT NULL "
            "ORDER BY workout_day, id", (start, end)
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-analyze workouts, honoring manual matches")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--workout-id", type=int)
    parser.add_argument("--refresh-laps", action="store_true",
                        help="add lap markers from archived raw FIT files first")
    parser.add_argument("--no-ai", action="store_true",
                        help="only recompute execution scores/interval results (no LLM calls)")
    parser.add_argument("--db", help="override database path")
    args = parser.parse_args()

    db = WorkoutDatabase(args.db) if args.db else WorkoutDatabase()
    if args.workout_id:
        ids = [args.workout_id]
    elif args.start and args.end:
        ids = _workout_ids(db, args.start, args.end)
    else:
        parser.error("give --workout-id or --start/--end")

    laps_added = 0
    if args.refresh_laps:
        conn = sqlite3.connect(db.db_path)
        fit_ids = [r[0] for r in conn.execute(
            f"SELECT DISTINCT fit_file_id FROM workouts WHERE id IN ({','.join('?' * len(ids))})", ids)]
        conn.close()
        laps_added = sum(refresh_laps(fid, db) for fid in fit_ids if fid)
        print(f"Added lap markers to {laps_added} stored FIT files")

    done = 0
    for wid in ids:
        result = recompute_execution_only(wid, db) if args.no_ai else reanalyze_workout(wid, db)
        if result:
            done += 1
            score = result.get("execution_score") if args.no_ai else (result.get("execution") or {}).get("execution_score")
            print(f"  workout {wid}: execution score {score}")
    print(f"Processed {done}/{len(ids)} workouts")


if __name__ == "__main__":
    main()
