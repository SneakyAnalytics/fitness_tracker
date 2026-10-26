"""The React Admin page's endpoints: problems, deleting a workout, ride-file links, goals."""
import json
import sqlite3

from fastapi.testclient import TestClient

from src.api.app import app
from src.storage.database import WorkoutDatabase
from src.storage.events import record_event

client = TestClient(app)


def _workout(db_path, day, title):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO workouts (workout_day, workout_title, workout_data) VALUES (?, ?, ?)",
            (day, title, json.dumps({"metrics": {"actual_tss": 50, "actual_duration": 1.0}})))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def test_problems_can_be_listed_and_dismissed():
    record_event("warning", "admin-test", "sync was skipped")
    rows = client.get("/admin/events").json()["events"]
    mine = [e for e in rows if e["source"] == "admin-test"]
    assert mine and mine[0]["level"] == "warning"
    assert client.post("/admin/events/dismiss", json={"ids": [e["id"] for e in mine]}).json()["dismissed"] == len(mine)
    assert not [e for e in client.get("/admin/events").json()["events"] if e["source"] == "admin-test"]


def test_delete_workout_removes_it_and_404s_when_missing():
    path = WorkoutDatabase().db_path
    wid = _workout(path, "2026-03-02", "Doomed")
    listed = client.get("/admin/workouts", params={"start_date": "2026-03-02", "end_date": "2026-03-02"}).json()["workouts"]
    assert any(w["id"] == wid for w in listed)
    assert client.delete(f"/admin/workouts/{wid}").status_code == 200
    listed = client.get("/admin/workouts", params={"start_date": "2026-03-02", "end_date": "2026-03-02"}).json()["workouts"]
    assert not any(w["id"] == wid for w in listed)
    assert client.delete(f"/admin/workouts/{wid}").status_code == 404


def test_ride_file_can_be_moved_and_removed():
    path = WorkoutDatabase().db_path
    conn = sqlite3.connect(path)
    try:
        conn.execute("INSERT INTO fit_files (file_name, workout_day, workout_title, fit_data) VALUES (?, ?, ?, ?)",
                     ("ride.fit.gz", "2026-03-03", "Ride", json.dumps({"metrics": {"tss": 80, "duration": 1.5}})))
        conn.commit()
        fit_id = conn.execute("SELECT id FROM fit_files WHERE file_name = 'ride.fit.gz'").fetchone()[0]
    finally:
        conn.close()
    wid = _workout(path, "2026-03-03", "Ride")

    avail = client.get("/admin/fit-files", params={"date": "2026-03-03"}).json()["fit_files"]
    assert [f["id"] for f in avail] == [fit_id]
    assert client.post(f"/admin/workouts/{wid}/fit", json={"fit_file_id": fit_id}).status_code == 200
    row = [w for w in client.get("/admin/workouts", params={"start_date": "2026-03-03", "end_date": "2026-03-03"}).json()["workouts"] if w["id"] == wid][0]
    assert row["fit_file_id"] == fit_id and row["fit_tss"] == 80
    assert client.post(f"/admin/workouts/{wid}/fit", json={"fit_file_id": None}).status_code == 200
    row = [w for w in client.get("/admin/workouts", params={"start_date": "2026-03-03", "end_date": "2026-03-03"}).json()["workouts"] if w["id"] == wid][0]
    assert row["fit_file_id"] is None
    assert client.post("/admin/workouts/999999/fit", json={"fit_file_id": None}).status_code == 404


def test_goals_can_be_added_edited_and_completed():
    made = client.post("/admin/goals", json={"description": "Admin-test ride", "priority": 2, "target_date": "2027-05-01"})
    assert made.status_code == 200
    gid = made.json()["id"]
    assert client.post("/admin/goals", json={"description": "Bad date", "target_date": "soon"}).status_code == 400
    done = client.patch(f"/admin/goals/{gid}", json={"status": "completed", "progress_note": "Finished"}).json()
    assert done["status"] == "completed" and done["progress_notes"][-1].endswith("Finished")
    assert client.patch(f"/admin/goals/{gid}", json={"status": "nonsense"}).status_code == 400
    assert client.patch("/admin/goals/999999", json={"status": "paused"}).status_code == 404
    listed = client.get("/admin/goals").json()["goals"]
    assert any(g["id"] == gid for g in listed)
    assert not any(g["id"] == gid for g in client.get("/admin/goals", params={"include_inactive": False}).json()["goals"])
