"""Re-importing a TrainingPeaks export must not undo the review.

The upload deletes and re-inserts every workout in the CSV's date range. The nightly
sync re-imports the last three days, so without restore_workouts() a Sunday-night run
would wipe Sunday's confirmed matches and detach analyses from their workouts.
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import get_db_path
from src.utils.trainingpeaks_sync import append_strength_rows, strength_csv_rows

client = TestClient(app)

CSV = """Title,WorkoutType,WorkoutDay,TimeTotalInHours,TSS
Zwift - Monday Flush,Bike,2026-10-05,0.67,19
Cycling,Bike,2026-10-05,0.37,15
Cycling,Bike,2026-10-05,0.32,12
Sauna,Other,2026-10-05,0.25,
"""


def upload(text):
    r = client.post("/upload/workouts", files={"file": ("workouts.csv", text.encode(), "text/csv")})
    assert r.status_code == 200, r.text


def rows(conn):
    return conn.execute(
        "SELECT id, workout_title, sequence_number, proposed_workout_name, match_source FROM workouts "
        "WHERE workout_day = '2026-10-05' ORDER BY id").fetchall()


@pytest.fixture()
def conn():
    c = sqlite3.connect(get_db_path())
    c.execute("DELETE FROM workouts")
    c.execute("DELETE FROM workout_analyses")
    c.commit()
    yield c
    c.close()


def test_reimport_keeps_ids_matches_and_analyses(conn):
    upload(CSV)
    before = rows(conn)
    second_commute = before[2][0]
    conn.execute("UPDATE workouts SET proposed_workout_name = 'Commute from work', match_source = 'manual' "
                 "WHERE id = ?", (second_commute,))
    conn.execute("INSERT INTO workout_analyses (workout_id, analysis_text) VALUES (?, 'easy spin')",
                 (second_commute,))
    conn.commit()

    upload(CSV)
    after = rows(conn)
    assert [r[0] for r in after] == [r[0] for r in before]
    assert after[2][3:] == ("Commute from work", "manual")
    assert conn.execute("SELECT workout_id FROM workout_analyses").fetchone()[0] == second_commute


def test_new_workout_never_inherits_a_removed_workouts_id(conn):
    upload(CSV)
    sauna_id = rows(conn)[-1][0]
    conn.execute("INSERT INTO workout_analyses (workout_id, analysis_text) VALUES (?, 'sauna')", (sauna_id,))
    conn.commit()

    # Sauna deleted in TrainingPeaks; a strength session appears instead.
    upload(CSV.replace("Sauna,Other,2026-10-05,0.25,", "Strength,Strength,2026-10-05,0.53,20"))
    strength = [r for r in rows(conn) if r[1] == "Strength"][0]
    assert strength[0] != sauna_id


STRENGTH_FEED = [
    {"title": "Strength", "workoutType": "StructuredStrength", "startDateTime": "2026-10-05T07:13:08",
     "prescribedDate": "2026-10-05", "completedDateTime": "2026-10-05T07:44:49",
     "executedDurationInSeconds": 1901, "completedTss": 20.0, "completedIntensityFactor": 0.59},
    {"title": "Strength", "workoutType": "StructuredStrength", "startDateTime": "2026-09-23T06:47:15",
     "executedDurationInSeconds": 2333, "completedTss": 23.0},             # outside the range
    {"title": "Upper body", "prescribedDate": "2026-10-06", "executedDurationInSeconds": None},  # planned only
]


def test_strength_feed_rows_are_completed_and_in_range():
    got = strength_csv_rows(STRENGTH_FEED, "2026-10-04", "2026-10-06")
    assert len(got) == 1
    assert got[0]["WorkoutDay"] == "2026-10-05"
    assert got[0]["WorkoutType"] == "Strength"
    assert got[0]["TSS"] == 20.0
    assert abs(got[0]["TimeTotalInHours"] - 1901 / 3600) < 1e-3


def test_strength_rows_appended_once(tmp_path):
    path = tmp_path / "workouts.csv"
    path.write_bytes(b"\xef\xbb\xbf" + CSV.encode())
    new = strength_csv_rows(STRENGTH_FEED, "2026-10-04", "2026-10-06")
    assert append_strength_rows(path, new) == 1
    assert append_strength_rows(path, new) == 0  # already there
    text = path.read_bytes()
    assert text.startswith(b"\xef\xbb\xbf")
    lines = text.decode("utf-8-sig").splitlines()
    assert lines[0] == "Title,WorkoutType,WorkoutDay,TimeTotalInHours,TSS"
    assert lines[-1] == "Strength,Strength,2026-10-05,0.5281,20.0"
