"""Performance Manager projection: planned days use the plan, later days repeat recent load."""
import sqlite3
from datetime import date, timedelta

from src.storage.database import WorkoutDatabase
from src.utils import training_load as tl


def _insert(db_path, sql, args=()):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(sql, args)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def test_projection_follows_the_plan_then_assumes_recent_load():
    db_path = WorkoutDatabase().db_path
    today = date.today()
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM workouts")
    conn.execute("DELETE FROM proposed_workouts")
    conn.execute("DELETE FROM daily_plans")
    conn.execute("DELETE FROM weekly_plans WHERE weekNumber = 9001")
    conn.commit()
    conn.close()
    for back in range(1, 61):  # two steady months of 70 TSS a day
        day = (today - timedelta(days=back)).isoformat()
        _insert(db_path, "INSERT INTO workouts (workout_day, workout_title, workout_data) VALUES (?, 'Ride', ?)",
                (day, '{"metrics": {"actual_tss": 70}}'))
    _insert(db_path, "INSERT INTO weekly_plans (weekNumber, startDate, notes) VALUES (9001, ?, 'x')", (today.isoformat(),))
    for offset, lo, hi in ((1, 100, 140), (2, None, None)):   # tomorrow: hard day, the day after: rest
        plan = _insert(db_path, "INSERT INTO daily_plans (weekNumber, dayNumber, date) VALUES (9001, ?, ?)",
                       (offset, (today + timedelta(days=offset)).isoformat()))
        if lo:
            _insert(db_path, "INSERT INTO proposed_workouts (dailyPlanId, type, name, plannedTSS_min, plannedTSS_max)"
                             " VALUES (?, 'Bike', 'Hard', ?, ?)", (plan, lo, hi))

    out = tl.project_load(db_path, days=5)
    p = out["projection"]
    assert [r["kind"] for r in p] == ["planned", "planned", "assumed", "assumed", "assumed"]
    assert p[0]["tss"] == 120.0 and p[1]["tss"] == 0.0                # midpoint of 100-140; a planned rest day
    assert p[2]["tss"] == out["assumed_daily_tss"] > 0                # later days repeat recent load
    assert p[0]["ctl"] > out["history"][-1]["ctl"] * 0.99            # a 120 TSS day against ~70 CTL raises it
    assert p[1]["atl"] < p[0]["atl"]                                  # the rest day sheds fatigue
    assert p[1]["tsb"] == round(p[0]["ctl"] - p[0]["atl"], 1)         # form going into a day = yesterday's CTL - ATL
    assert out["plan_through"] == (today + timedelta(days=2)).isoformat()
    assert len(out["history"]) == 61                                  # first workout through today

    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM workouts"); conn.execute("DELETE FROM proposed_workouts")
    conn.execute("DELETE FROM daily_plans"); conn.execute("DELETE FROM weekly_plans WHERE weekNumber = 9001")
    conn.commit(); conn.close()
