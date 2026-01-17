"""Reanalyze workouts using fit_files.fit_data for richer visuals.

Usage (inside container):
  python -m src.utils.reanalyze_with_fit_data --start 2026-01-12 --end 2026-01-13
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime

from .fit_file_analyzer import FitFileAnalyzer
from ..storage.database import WorkoutDatabase


def main() -> None:
    parser = argparse.ArgumentParser(description="Reanalyze workouts with fit_data")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--db", default="/app/data/fitness_data.db", help="Path to SQLite DB")
    args = parser.parse_args()

    # Validate dates
    try:
        datetime.strptime(args.start, "%Y-%m-%d")
        datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError as exc:
        raise SystemExit("Invalid date format, expected YYYY-MM-DD") from exc

    db = WorkoutDatabase(args.db)
    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT w.id, w.workout_day, w.workout_title, w.fit_file_id, w.athlete_comments
        FROM workouts w
        WHERE w.workout_day BETWEEN ? AND ?
          AND w.fit_file_id IS NOT NULL
        ORDER BY w.workout_day, w.id
        """,
        (args.start, args.end),
    )
    workouts = cur.fetchall()

    analyzer = FitFileAnalyzer(use_dynamic_models=True)
    updated = 0

    for workout_id, workout_day, workout_title, fit_file_id, athlete_comments in workouts:
        cur.execute("SELECT fit_data FROM fit_files WHERE id = ?", (fit_file_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            print(f"⚠️  Missing fit_data for fit_file_id={fit_file_id} ({workout_title})")
            continue

        fit_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        if fit_data is not None:
            fit_data['title'] = workout_title
            fit_data['workout_day'] = workout_day
            if athlete_comments:
                fit_data['athlete_comments'] = athlete_comments
        analysis = analyzer.analyze_workout_from_parsed_data(
            parsed_data=fit_data,
            athlete_notes=athlete_comments
        )
        if not analysis:
            print(f"⚠️  Analysis failed for {workout_title}")
            continue

        db.store_workout_analysis(
            workout_id=workout_id,
            fit_file_id=fit_file_id,
            analysis_text=analysis.get("ai_analysis", ""),
            analysis_data=analysis,
            peak_efforts=analysis.get("peak_efforts"),
        )
        updated += 1
        print(f"✅ Reanalyzed {workout_day} - {workout_title}")

    conn.close()
    print(f"✅ Reanalysis complete. Updated {updated} workouts.")


if __name__ == "__main__":
    main()
