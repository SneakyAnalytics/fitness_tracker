"""Database inspection utility for workout analyses.

Usage (inside container):
  python -m src.utils.db_inspect --start 2026-01-12 --end 2026-01-13

Usage (host with docker):
  docker exec fitness-tracker-api python -m src.utils.db_inspect --start 2026-01-12 --end 2026-01-13
"""
from __future__ import annotations

import argparse
import sqlite3
from typing import Optional


def run_query(cur: sqlite3.Cursor, query: str, params: tuple = ()):
    cur.execute(query, params)
    rows = cur.fetchall()
    for row in rows:
        print(dict(row))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect workout analyses and matching data")
    parser.add_argument("--db", default="/app/data/fitness_data.db", help="Path to SQLite DB")
    parser.add_argument("--start", default="2026-01-12", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-01-13", help="End date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=20, help="Limit for recent analyses")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("=== Recent analyses ===")
    run_query(
        cur,
        """
        SELECT wa.id, wa.analyzed_at, wa.workout_id, wa.fit_file_id,
               w.workout_day, w.workout_title, f.file_name,
               substr(wa.analysis_text, 1, 80) as analysis_preview
        FROM workout_analyses wa
        LEFT JOIN workouts w ON wa.workout_id = w.id
        LEFT JOIN fit_files f ON wa.fit_file_id = f.id
        ORDER BY wa.analyzed_at DESC
        LIMIT ?
        """,
        (args.limit,),
    )

    print("\n=== Duplicates by workout_id ===")
    run_query(
        cur,
        """
        SELECT workout_id, COUNT(*) as cnt
        FROM workout_analyses
        WHERE workout_id IS NOT NULL
        GROUP BY workout_id
        HAVING cnt > 1
        ORDER BY cnt DESC
        LIMIT 50
        """,
    )

    print("\n=== Duplicates by fit_file_id ===")
    run_query(
        cur,
        """
        SELECT fit_file_id, COUNT(*) as cnt
        FROM workout_analyses
        WHERE fit_file_id IS NOT NULL
        GROUP BY fit_file_id
        HAVING cnt > 1
        ORDER BY cnt DESC
        LIMIT 50
        """,
    )

    print(f"\n=== Workouts ({args.start} to {args.end}) ===")
    run_query(
        cur,
        """
        SELECT id, workout_day, workout_title, proposed_workout_name, fit_file_id,
               json_extract(workout_data, '$.type') as type,
               json_extract(workout_data, '$.metrics.actual_duration') as duration,
               json_extract(workout_data, '$.metrics.actual_tss') as tss
        FROM workouts
        WHERE workout_day BETWEEN ? AND ?
        ORDER BY workout_day, id
        """,
        (args.start, args.end),
    )

    print(f"\n=== Workouts missing fit_file_id ({args.start} to {args.end}) ===")
    run_query(
        cur,
        """
        SELECT id, workout_day, workout_title,
               json_extract(workout_data, '$.metrics.actual_duration') as duration,
               json_extract(workout_data, '$.metrics.actual_tss') as tss
        FROM workouts
        WHERE workout_day BETWEEN ? AND ?
          AND fit_file_id IS NULL
        ORDER BY workout_day, id
        """,
        (args.start, args.end),
    )

    print(f"\n=== FIT files ({args.start} to {args.end}) ===")
    run_query(
        cur,
        """
        SELECT id, workout_day, file_name
        FROM fit_files
        WHERE workout_day BETWEEN ? AND ?
        ORDER BY workout_day, id
        """,
        (args.start, args.end),
    )

    print(f"\n=== Analyses ({args.start} to {args.end}) ===")
    run_query(
        cur,
        """
        SELECT wa.id, wa.analyzed_at, wa.workout_id, wa.fit_file_id,
               w.workout_day, w.workout_title, f.file_name,
               substr(wa.analysis_text, 1, 80) as analysis_preview
        FROM workout_analyses wa
        LEFT JOIN workouts w ON wa.workout_id = w.id
        LEFT JOIN fit_files f ON wa.fit_file_id = f.id
        WHERE w.workout_day BETWEEN ? AND ?
           OR f.workout_day BETWEEN ? AND ?
        ORDER BY wa.analyzed_at DESC
        """,
        (args.start, args.end, args.start, args.end),
    )

    conn.close()


if __name__ == "__main__":
    main()
