"""Ride files must only ever attach to the session they recorded.

Week of 2026-10-05: Saturday's 4-hour gravel ride was uploaded after midnight UTC,
so its file is stored under Sunday. The weekly summary guessed "any file on the
same day" for Sunday's sauna, saved that link, and counted the ride twice
(735 TSS / 17.5 h instead of 520 / 12.9).
"""
import json
import sqlite3

import pytest

from src.config import get_db_path
from src.storage.database import WorkoutDatabase
from src.storage.workout_matching import link_fit_files, repair_fit_links


def fit(conn, stored_day, name, sport, start_utc, minutes, tss=None):
    data = {"sport": sport, "start_time": start_utc, "metrics": {"duration": minutes, "tss": tss}}
    return conn.execute("INSERT INTO fit_files (workout_day, workout_title, fit_data, file_name) VALUES (?, ?, ?, ?)",
                        (stored_day, name, json.dumps(data), name)).lastrowid


def workout(conn, day, title, wtype, minutes, tss=None, fit_id=None):
    data = {"title": title, "type": wtype, "metrics": {"actual_duration": minutes, "actual_tss": tss}}
    return conn.execute("INSERT INTO workouts (workout_day, workout_title, workout_data, sequence_number, fit_file_id)"
                        " VALUES (?, ?, ?, 1, ?)", (day, title, json.dumps(data), fit_id)).lastrowid


@pytest.fixture()
def week():
    db = WorkoutDatabase()
    conn = sqlite3.connect(get_db_path())
    for t in ("workouts", "fit_files", "workout_analyses"):
        conn.execute(f"DELETE FROM {t}")
    ids = {}
    # Saturday 09:06 PT ride, stored under Sunday (UTC upload date).
    ids["gravel_fit"] = fit(conn, "2026-10-11", "Garmin-gravel.FIT", "cycling", "2026-10-10T16:06:47", 264.8, 215)
    ids["yoga_fit"] = fit(conn, "2026-10-08", "Garmin-yoga.FIT", "training", "2026-10-08T13:08:07", 45.1)
    ids["ride_fit"] = fit(conn, "2026-10-08", "Garmin-ride.FIT", "cycling", "2026-10-08T15:16:51", 44.9)
    ids["gravel"] = workout(conn, "2026-10-10", "Gravel Cycling", "Bike", 254.5, 204.57, ids["gravel_fit"])
    # The bad links the old code left behind:
    ids["sauna"] = workout(conn, "2026-10-11", "Sauna", "Other", 20, None, ids["gravel_fit"])
    ids["yoga"] = workout(conn, "2026-10-08", "Yoga", "Other", 45.08, 22.48, ids["ride_fit"])
    ids["ride"] = workout(conn, "2026-10-08", "Cycling", "Bike", 44.0, 30.0, ids["yoga_fit"])
    conn.commit()
    yield db, conn, ids
    conn.close()


def links(conn):
    return dict(conn.execute("SELECT id, fit_file_id FROM workouts"))


def test_repair_puts_each_file_on_its_own_session(week):
    db, conn, ids = week
    result = repair_fit_links(get_db_path(), "2026-10-05", "2026-10-11")
    now = links(conn)
    assert now[ids["sauna"]] is None
    assert now[ids["gravel"]] == ids["gravel_fit"]
    assert now[ids["yoga"]] == ids["yoga_fit"]
    assert now[ids["ride"]] == ids["ride_fit"]
    assert result["cross_day"] + result["wrong_sport"] >= 3


def test_weekly_summary_counts_trainingpeaks_tss_once_and_guesses_nothing(week):
    db, conn, ids = week
    conn.execute("UPDATE workouts SET fit_file_id = NULL WHERE id = ?", (ids["sauna"],))
    conn.commit()
    summary = db.generate_weekly_summary("2026-10-05", "2026-10-11")
    assert summary["total_tss"] == pytest.approx(204.57 + 22.48 + 30.0, abs=0.1)
    assert summary["total_training_hours"] == pytest.approx((254.5 + 20 + 45.08 + 44.0) / 60, abs=0.05)
    assert links(conn)[ids["sauna"]] is None  # the summary must not attach a file


def test_linker_never_gives_a_sauna_or_yoga_a_ride_file(week):
    db, conn, ids = week
    conn.execute("UPDATE workouts SET fit_file_id = NULL")
    conn.commit()
    link_fit_files(get_db_path(), "2026-10-05", "2026-10-11")
    now = links(conn)
    assert now[ids["sauna"]] is None
    assert now[ids["yoga"]] == ids["yoga_fit"]
    assert now[ids["ride"]] == ids["ride_fit"]
    assert now[ids["gravel"]] == ids["gravel_fit"]
