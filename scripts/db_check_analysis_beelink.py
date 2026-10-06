#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path('/app/data/fitness_data.db')
WORKOUT_ID = 563

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute(
        "SELECT id, workout_day, workout_title, json_extract(workout_data, '$.type') AS type, json_extract(workout_data, '$.sport') AS sport FROM workouts WHERE id = ?",
        (WORKOUT_ID,)
    ).fetchone()

    print("Workout:")
    if row:
        print(dict(row))
    else:
        print("Not found")

    analysis = cur.execute(
        "SELECT id, workout_id, fit_file_id, analyzed_at FROM workout_analyses WHERE workout_id = ?",
        (WORKOUT_ID,)
    ).fetchone()

    print("\nAnalysis:")
    print(dict(analysis) if analysis else "None")

    conn.close()

if __name__ == "__main__":
    main()
