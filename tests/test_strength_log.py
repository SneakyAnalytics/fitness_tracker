"""Logged lifts are indexed by exercise name so weights can follow an athlete from week to week."""
import json
import sqlite3

from fastapi.testclient import TestClient

from src.api.app import app
from src.storage import strength_log as sl
from src.storage.database import WorkoutDatabase
from src.utils import coach_tools

client = TestClient(app)

SECTIONS = [
    {"name": "Warmup", "exercises": [{"name": "Leg Swings", "sets": [{"reps": "12", "weight": "bodyweight"}]}]},
    {"name": "Main", "exercises": [{"name": "Goblet Squat", "sets": [{"sets": 3, "reps": "8-10", "weight": "moderate"}]},
                                   {"name": "Romanian Deadlift", "sets": [{"sets": 3, "reps": "8-10", "weight": "moderate"}]}]},
]


def _plan(path, plan_id, sections=SECTIONS):
    conn = sqlite3.connect(path)
    try:
        conn.execute("DELETE FROM proposed_workouts WHERE id = ?", (plan_id,))
        conn.execute("INSERT INTO proposed_workouts (id, dailyPlanId, type, name, sections) VALUES (?, 1, 'strength', ?, ?)",
                     (plan_id, f"Lower {plan_id}", json.dumps(sections)))
        conn.execute("DELETE FROM strength_log WHERE planned_workout_id = ?", (plan_id,))
        conn.commit()
    finally:
        conn.close()


def test_parsing_weights_and_reps():
    assert sl.parse_weight("45 lbs") == 45 and sl.parse_weight("45-50") == 50 and sl.parse_weight(22.5) == 22.5
    assert sl.parse_weight("bodyweight") is None and sl.parse_weight("") is None and sl.parse_weight("0") is None
    assert sl.parse_reps("10, 10, 8") == [10, 10, 8] and sl.parse_reps("24") == [24] and sl.parse_reps("10-12") == [12]
    assert sl.parse_reps("") == [] and sl.parse_reps(None) == []
    assert sl.exercise_key("Goblet  Squat!") == sl.exercise_key("goblet-squat") == "goblet squat"


def test_a_save_is_indexed_by_exercise_name_even_for_old_positional_logs():
    path = WorkoutDatabase().db_path
    _plan(path, 7001)
    # positions 1 and 2 are Goblet Squat and Romanian Deadlift (position 0 is the warmup movement)
    perf = {"exercises": {"0": {"reps": "", "weight": "", "notes": ""},
                          "1": {"reps": "10, 10, 8", "weight": "45", "notes": "felt good"},
                          "2": {"name": "Romanian Deadlift", "sets": [{"weight": "60", "reps": "10"}, {"weight": "65", "reps": "8"}]}}}
    r = client.post("/workout/performance", json={"workout_id": 7001, "workout_date": "2026-10-20", "performance_data": perf})
    assert r.status_code == 200
    last = client.get("/strength/last", params=[("name", "goblet squat"), ("name", "Romanian Deadlift"), ("name", "Leg Swings")]).json()["last"]
    assert set(last) == {"goblet squat", "Romanian Deadlift"}           # the empty warmup entry wasn't recorded
    squat = last["goblet squat"]
    assert squat["top_weight"] == 45 and [s["reps"] for s in squat["sets"]] == [10, 10, 8] and squat["notes"] == "felt good"
    assert last["Romanian Deadlift"]["top_weight"] == 65
    assert sl.describe(squat) == "45 lb × 10, 10, 8"            # typed per set
    assert sl.describe({"sets": [{"weight": 45.0, "reps": 24, "total": True}]}) == "45 lb × 24 total"
    assert sl.describe(last["Romanian Deadlift"]) == "60/65 lb × 10, 8"
    # saving again replaces, it doesn't duplicate
    perf["exercises"]["1"]["weight"] = "50"
    client.post("/workout/performance", json={"workout_id": 7001, "workout_date": "2026-10-20", "performance_data": perf})
    assert client.get("/strength/last", params={"name": "Goblet Squat"}).json()["last"]["Goblet Squat"]["top_weight"] == 50
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM strength_log WHERE planned_workout_id = 7001").fetchone()[0] == 2
    conn.close()


def test_history_the_coach_tool_and_the_prompt_section():
    path = WorkoutDatabase().db_path
    _plan(path, 7002)
    conn = sqlite3.connect(path)
    conn.execute("DELETE FROM strength_log WHERE exercise_key = 'goblet squat'")
    for pid, day, w in ((7101, "2026-10-06", 40), (7102, "2026-10-13", 45), (7103, "2026-10-20", 50)):
        conn.execute("INSERT INTO strength_log (planned_workout_id, log_date, exercise_key, exercise_name, sets_json, top_weight)"
                     " VALUES (?, ?, 'goblet squat', 'Goblet Squat', ?, ?)", (pid, day, json.dumps([{"weight": w, "reps": 10}] * 3), w))
    conn.commit(); conn.close()
    from datetime import date
    hist = sl.history("Goblet Squat", db_path=path, today=date(2026, 10, 27))
    assert [s["top_weight"] for s in hist["Goblet Squat"]] == [50, 45, 40]              # newest first
    out = json.loads(coach_tools.run_tool("get_strength_history", {"exercise": "goblet squat", "weeks": 520}, path))
    assert out["exercises"]["Goblet Squat"][0]["summary"] == "50 lb × 10, 10, 10"
    text = sl.prompt_summary(path, weeks=520)
    assert "Goblet Squat: 10-06 40 lb × 10, 10, 10 · 10-13 45 lb" in text and "specific weight in lb" in text
    assert "get_strength_history" in {t["name"] for t in coach_tools.TOOLS}
    conn = sqlite3.connect(path)
    for pid, name, reps in ((7201, "Plank", 40), (7202, "Cat-Cow", 1)):
        conn.execute("INSERT INTO strength_log (planned_workout_id, log_date, exercise_key, exercise_name, sets_json)"
                     " VALUES (?, '2026-10-20', ?, ?, ?)", (pid, name.lower(), name, json.dumps([{"weight": None, "reps": reps}])))
    conn.commit(); conn.close()
    text = sl.prompt_summary(path, weeks=520)
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO strength_log (planned_workout_id, log_date, exercise_key, exercise_name, sets_json, notes)"
                 " VALUES (7203, '2026-10-21', 'low lunge', 'Low Lunge', ?, 'hold')", (json.dumps([{"weight": None, "reps": 90}] * 2),))
    conn.commit(); conn.close()
    text = sl.prompt_summary(path, weeks=520)
    assert "Bodyweight work, latest reps: Plank 40" in text and "Cat-Cow" not in text
    assert "Low Lunge" not in text                                       # a timed stretch isn't progression
    assert sl.describe({"sets": [{"weight": None, "reps": 90}] * 2, "notes": "hold"}) == "hold 90, 90 s"   # a ticked stretch isn't a count
    conn = sqlite3.connect(path); conn.execute("DELETE FROM strength_log WHERE planned_workout_id IN (7201, 7202, 7203)"); conn.commit(); conn.close()


def test_backfill_flattens_existing_logs_and_skips_old_shapes():
    path = WorkoutDatabase().db_path
    _plan(path, 7003)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS workout_performance (id INTEGER PRIMARY KEY AUTOINCREMENT, workout_id INTEGER NOT NULL,"
                 " workout_date TEXT NOT NULL, actual_duration INTEGER, performance_data TEXT, UNIQUE(workout_id, workout_date))")
    conn.execute("DELETE FROM workout_performance WHERE workout_id IN (7003, 7004)")
    conn.execute("INSERT INTO workout_performance (workout_id, workout_date, performance_data) VALUES (7003, '2026-10-21', ?)",
                 (json.dumps({"exercises": {"2": {"reps": "8", "weight": "100", "notes": ""}}}),))
    conn.execute("INSERT INTO workout_performance (workout_id, workout_date, performance_data) VALUES (7004, '2025-03-05', ?)",
                 (json.dumps({"sections": [], "general_notes": "old"}),))
    result = sl.backfill(conn)
    row = conn.execute("SELECT exercise_name, top_weight FROM strength_log WHERE planned_workout_id = 7003").fetchone()
    conn.execute("DELETE FROM workout_performance WHERE workout_id IN (7003, 7004)")
    conn.commit(); conn.close()
    assert row == ("Romanian Deadlift", 100.0)
    assert result["logs_skipped"] >= 1
