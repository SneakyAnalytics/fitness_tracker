#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path('/app/data/fitness_data.db')


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
    SELECT id, workout_day, workout_title,
           json_extract(workout_data, '$.type') AS type,
           json_extract(workout_data, '$.sport') AS sport
    FROM workouts
    WHERE lower(workout_title) LIKE '%ski%'
       OR lower(workout_title) LIKE '%cross%'
       OR lower(json_extract(workout_data, '$.sport')) LIKE '%ski%'
    ORDER BY workout_day DESC
    LIMIT 10
    """
    rows = cur.execute(query).fetchall()

    print(f"Found {len(rows)} skiing/cross-country candidates")
    for r in rows:
        print("---")
        print("ID:", r["id"])
        print("Date:", r["workout_day"])
        print("Title:", r["workout_title"])
        print("Type:", r["type"])
        print("Sport:", r["sport"])

    if not rows:
        print("No matches found in workouts table.")

    conn.close()


if __name__ == "__main__":
    main()
