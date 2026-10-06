"""Regression tests for manual workout matching.

The manual-match lookup once queried snake_case columns that don't exist; the
error was swallowed and every manual match was silently replaced by AI matching.
"""
import json
import sqlite3

import pytest

from src.config import get_db_path
from src.storage.database import WorkoutDatabase
from src.storage.workout_matching import match_workout_to_proposed
from src.utils.fit_file_analyzer import FitFileAnalyzer

INTERVALS = [{"name": "Tempo 1", "duration": 900,
              "powerTarget": {"type": "range", "min": 233, "max": 260, "unit": "watts"}}]


@pytest.fixture()
def seeded():
    db = WorkoutDatabase()
    conn = sqlite3.connect(get_db_path())
    conn.execute("DELETE FROM workouts")
    conn.execute("DELETE FROM proposed_workouts")
    conn.execute("DELETE FROM daily_plans")
    conn.execute("DELETE FROM weekly_plans")
    conn.execute("INSERT INTO weekly_plans (weekNumber, startDate, notes, ftp) VALUES (90, '2026-09-21', '', 302)")
    conn.execute("INSERT INTO weekly_plans (weekNumber, startDate, notes, ftp) VALUES (91, '2026-09-28', '', 310)")
    ids = {}
    for week, date, name, wtype in [
        (90, "2026-09-25", "Tempo Progression", "bike"),
        (90, "2026-09-25", "Recovery Spin", "bike"),
        (91, "2026-09-30", "Tempo Progression", "bike"),  # same name, next week
    ]:
        cur = conn.execute("INSERT INTO daily_plans (weekNumber, dayNumber, date) VALUES (?, 5, ?)", (week, date))
        cur = conn.execute(
            "INSERT INTO proposed_workouts (dailyPlanId, type, name, plannedDuration, plannedTSS_min, plannedTSS_max,"
            " intervals, prescribed_ftp) VALUES (?, ?, ?, 60, 50, 60, ?, NULL)",
            (cur.lastrowid, wtype, name, json.dumps(INTERVALS)),
        )
        ids[(date, name)] = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO workouts (workout_day, workout_title, workout_data) VALUES ('2026-09-25', 'Zwift ride', '{}')"
    )
    ids["workout"] = cur.lastrowid
    conn.commit()
    conn.close()
    return db, ids


def analyzer():
    return FitFileAnalyzer.__new__(FitFileAnalyzer)  # lookups only, no Gemini client


def test_name_lookup_uses_real_schema_and_prefers_same_day(seeded):
    _, ids = seeded
    found = analyzer()._load_proposed_workout_by_name("Tempo Progression", "2026-09-25")
    assert found["id"] == ids[("2026-09-25", "Tempo Progression")]
    assert found["intervals"] == INTERVALS
    assert found["prescribed_ftp"] == 302  # falls back to the week's FTP


def test_id_lookup_is_exact(seeded):
    _, ids = seeded
    pid = ids[("2026-09-30", "Tempo Progression")]
    found = analyzer()._load_proposed_workout_by_id(pid)
    assert found["id"] == pid and found["date"] == "2026-09-30"
    assert found["prescribed_ftp"] == 310


def test_date_fallback_refuses_to_guess_between_two_bike_workouts(seeded):
    assert analyzer()._load_proposed_workout("2026-09-25") is None


def test_match_records_id_and_is_returned_for_analysis(seeded):
    db, ids = seeded
    pid = ids[("2026-09-25", "Tempo Progression")]
    assert match_workout_to_proposed(get_db_path(), ids["workout"], "Tempo Progression", "manual",
                                     proposed_workout_id=pid)
    assert db.get_workout_match(ids["workout"]) == {
        "proposed_workout_id": pid, "proposed_workout_name": "Tempo Progression", "match_source": "manual"}


def test_explicit_match_never_falls_back_to_auto_matching(seeded, monkeypatch):
    _, ids = seeded
    a = analyzer()
    a.last_model_used = None
    calls = []
    monkeypatch.setattr(a, "_find_best_matching_workout", lambda *args, **kw: calls.append("auto"))
    monkeypatch.setattr(a, "_detect_peak_efforts", lambda *args, **kw: {})
    monkeypatch.setattr(a, "_detect_intervals", lambda *args, **kw: {})
    captured = {}

    def fake_ai(parsed, peaks, notes, intervals, proposed_workout=None, allow_date_fallback=True, **kw):
        captured["proposed"] = proposed_workout
        captured["fallback"] = allow_date_fallback
        return "ok"

    monkeypatch.setattr(a, "_generate_ai_analysis", fake_ai)
    monkeypatch.setattr(a, "_get_csv_tss_for_workout", lambda *args: None)
    parsed = {"sport": "cycling", "workout_date": "2026-09-25", "power_metrics": {"power_series": [200] * 60}}

    # A custom label for an unplanned session: analyze standalone, don't auto-match.
    result = a.analyze_workout_from_parsed_data(dict(parsed), matched_proposed_workout_name="Commute home")
    assert calls == [] and captured["proposed"] is None and captured["fallback"] is False
    assert result["proposed_workout"] is None

    pid = ids[("2026-09-25", "Tempo Progression")]
    a.analyze_workout_from_parsed_data(dict(parsed), matched_proposed_workout_id=pid)
    assert calls == [] and captured["proposed"]["id"] == pid


def test_fit_linking_rules():
    from src.storage.workout_matching import link_fit_files
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM workouts")
    conn.execute("DELETE FROM fit_files")

    def workout(day, title, tss, minutes):
        return conn.execute(
            "INSERT INTO workouts (workout_day, workout_title, workout_data) VALUES (?, ?, ?)",
            (day, title, json.dumps({"metrics": {"actual_tss": tss, "actual_duration": minutes}}))).lastrowid

    def fit(day, name, tss, minutes):
        return conn.execute(
            "INSERT INTO fit_files (workout_day, workout_title, fit_data, file_name) VALUES (?, ?, ?, ?)",
            (day, name, json.dumps({"metrics": {"tss": tss, "duration": minutes}}), name)).lastrowid

    zwift_w = workout("2026-09-29", "Zwift - Sweet Spot", 100, 90)
    strength_w = workout("2026-09-29", "Strength", 20, 40)
    evening_w = workout("2026-09-30", "Road Cycling", 40, 60)   # recorded next day in UTC
    zwift_f = fit("2026-09-29", "zwift-activity-1.fit", 98, 91)
    garmin_f = fit("2026-10-01", "tp-1.2026-10-01-02-00Z.GarminPing.FIT", 35, 58)
    taken_f = fit("2026-09-29", "zwift-activity-2.fit", 100, 90)
    other = workout("2026-09-28", "Zwift - Other", 100, 90)
    conn.execute("UPDATE workouts SET fit_file_id = ? WHERE id = ?", (taken_f, other))
    conn.commit()
    conn.close()

    assert link_fit_files(db_path, "2026-09-29", "2026-09-30") == 2
    conn = sqlite3.connect(db_path)
    links = dict(conn.execute("SELECT id, fit_file_id FROM workouts").fetchall())
    conn.close()
    assert links[zwift_w] == zwift_f        # not the already-linked twin
    assert links[strength_w] is None        # strength never gets a FIT
    assert links[evening_w] == garmin_f     # +1 day UTC drift allowed


def test_double_linked_fit_file_stays_with_the_ride():
    from src.storage.workout_matching import fix_double_linked_fit_files
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM workouts")
    conn.execute("DELETE FROM fit_files")
    fid = conn.execute("INSERT INTO fit_files (workout_day, workout_title, fit_data, file_name) VALUES "
                       "('2026-04-06', 'z', ?, 'zwift-activity-9.fit')",
                       (json.dumps({"duration_seconds": 2700}),)).lastrowid
    ride = conn.execute("INSERT INTO workouts (workout_day, workout_title, workout_data, fit_file_id) VALUES "
                        "('2026-04-06', 'Zwift - Easy Spin', ?, ?)",
                        (json.dumps({"type": "Bike", "metrics": {"actual_duration": 45}}), fid)).lastrowid
    yoga = conn.execute("INSERT INTO workouts (workout_day, workout_title, workout_data, fit_file_id) VALUES "
                        "('2026-04-06', 'Yoga', ?, ?)",
                        (json.dumps({"type": "Other", "metrics": {"actual_duration": 45}}), fid)).lastrowid
    conn.commit()
    conn.close()
    changes = fix_double_linked_fit_files(db_path, apply=True)
    assert [c["unlink_workout"] for c in changes] == [yoga]
    conn = sqlite3.connect(db_path)
    links = dict(conn.execute("SELECT id, fit_file_id FROM workouts").fetchall())
    conn.close()
    assert links == {ride: fid, yoga: None}
