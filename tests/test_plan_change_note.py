"""A deliberate plan change keeps its reason, so the coach doesn't read a substitution as a failed session."""
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import get_db_path
from src.storage.database import WorkoutDatabase
from src.utils.week_review import apply_match, review_week

client = TestClient(app)


@pytest.fixture()
def db():
    d = WorkoutDatabase()
    conn = sqlite3.connect(get_db_path())
    for t in ("workouts", "proposed_workouts", "daily_plans", "weekly_plans"):
        conn.execute(f"DELETE FROM {t}")
    conn.execute("INSERT INTO weekly_plans (weekNumber, startDate, notes, ftp) VALUES (99, '2026-10-12', '', 314)")
    cur = conn.execute("INSERT INTO daily_plans (weekNumber, dayNumber, date) VALUES (99, 3, '2026-10-14')")
    conn.execute("INSERT INTO proposed_workouts (dailyPlanId, type, name, plannedDuration, plannedTSS_min, plannedTSS_max) "
                 "VALUES (?, 'bike', 'Sweet Spot Sharpener', 80, 72, 78)", (cur.lastrowid,))
    data = json.dumps({"type": "Bike", "metrics": {"actual_duration": 95, "actual_tss": 90}})
    conn.execute("INSERT INTO workouts (workout_day, workout_title, workout_data, sequence_number) "
                 "VALUES ('2026-10-14', 'Outdoor ride', ?, 1)", (data,))
    conn.commit()
    wid = conn.execute("SELECT id FROM workouts").fetchone()[0]
    yield d, conn, wid
    conn.close()


def row_note(wid):
    return next(r for r in review_week("2026-10-12")["workouts"] if r["id"] == wid)["note"]


def test_note_is_saved_cleared_and_left_alone(db):
    _, _, wid = db
    apply_match(wid, None, "Outdoor ride instead", note="Dry window, took the sweet spot outside")
    assert row_note(wid) == "Dry window, took the sweet spot outside"
    apply_match(wid, None, "Outdoor ride instead")                      # re-confirming without a note keeps it
    assert row_note(wid) == "Dry window, took the sweet spot outside"
    apply_match(wid, None, "Outdoor ride instead", note="   ")          # a blank note clears it
    assert row_note(wid) is None


def test_long_notes_are_trimmed_and_the_endpoint_validates(db):
    _, _, wid = db
    apply_match(wid, None, "Outdoor ride instead", note="x" * 900)
    assert len(row_note(wid)) == 500
    r = client.post("/review/match", json={"workout_id": wid, "label": "Outdoor ride", "note": "y" * 501})
    assert r.status_code == 422
    ok = client.post("/review/match", json={"workout_id": wid, "label": "Outdoor ride", "note": "Rain at 6am"})
    assert ok.status_code == 200 and row_note(wid) == "Rain at 6am"


def test_the_weekly_summary_and_prompt_carry_the_reason(db):
    d, _, wid = db
    apply_match(wid, None, "Outdoor ride instead", note="Took it outside, dry window")
    changes = d._plan_changes("2026-10-12", "2026-10-18")
    assert changes == [{"date": "2026-10-14", "title": "Outdoor ride", "planned": "Outdoor ride instead",
                        "note": "Took it outside, dry window"}]
    from src.utils.ai_prompts import AICoachPrompts, PromptContext
    ctx = PromptContext(athlete_profile={}, coaching_notes={}, comprehensive_context={}, weekly_summary={"start_date": "2026-10-12", "end_date": "2026-10-18", "total_tss": 90,
                                        "total_training_hours": 1.6, "sessions_completed": 1,
                                        "qualitative_feedback": [{"type": "Bike", "title": "Outdoor ride", "date": "2026-10-14", "feedback": {}}],
                                        "plan_changes": changes})
    text = AICoachPrompts()._build_training_context(ctx)
    assert "Plan Changes the Athlete Made On Purpose" in text and "Took it outside, dry window" in text
    assert "Do not treat them as missed" in text
