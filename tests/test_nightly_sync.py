import json
import sqlite3
from datetime import date

from src.config import get_db_path


def test_nightly_analyzes_planned_rides_with_suggestion_and_skips_commutes(monkeypatch):
    from src.utils import nightly_sync, reanalyze

    today = date.today().isoformat()
    conn = sqlite3.connect(get_db_path())
    for t in ("workouts", "fit_files", "proposed_workouts", "daily_plans", "weekly_plans", "workout_analyses"):
        conn.execute(f"DELETE FROM {t}")
    conn.execute("INSERT INTO weekly_plans (weekNumber, startDate, notes, ftp) VALUES (1, ?, '', 306)", (today,))
    dp = conn.execute("INSERT INTO daily_plans (weekNumber, dayNumber, date) VALUES (1, 1, ?)", (today,)).lastrowid
    pw = conn.execute("INSERT INTO proposed_workouts (dailyPlanId, type, name, plannedDuration) VALUES "
                      "(?, 'bike', 'Tempo Builder', 60)", (dp,)).lastrowid

    def ride(title, minutes, seq):
        fid = conn.execute("INSERT INTO fit_files (workout_day, workout_title, fit_data, file_name) VALUES (?, ?, '{}', 'f')",
                           (today, f"{title}-{seq}")).lastrowid
        return conn.execute(
            "INSERT INTO workouts (workout_day, workout_title, workout_data, fit_file_id, sequence_number) "
            "VALUES (?, ?, ?, ?, ?)",
            (today, title, json.dumps({"type": "Bike", "metrics": {"actual_duration": minutes}}), fid, seq)).lastrowid

    zwift = ride("Zwift - Tempo Builder", 60, 1)
    commute = ride("Cycling", 20, 1)
    conn.commit()
    conn.close()

    calls = []
    monkeypatch.setattr(reanalyze, "reanalyze_workout",
                        lambda wid, db, analyzer, suggested_plan_id=None: calls.append((wid, suggested_plan_id)) or {})
    import src.utils.fit_file_analyzer as fa
    monkeypatch.setattr(fa, "FitFileAnalyzer", lambda **kw: object())
    monkeypatch.setattr(nightly_sync, "refresh_all", lambda path: None)

    result = nightly_sync.run(days=1, sync=False)
    assert calls == [(zwift, pw)]  # commute skipped
    assert result["errors"] == []
    conn = sqlite3.connect(get_db_path())
    assert conn.execute("SELECT COUNT(*) FROM workouts WHERE match_source = 'manual'").fetchone()[0] == 0
    conn.close()
    assert commute
