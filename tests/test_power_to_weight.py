"""W/kg from FTP and a week of scale readings, with progress toward a target."""
import json
import sqlite3
from datetime import date, timedelta

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.coach_routes import _wkg_target
from src.storage import goals
from src.storage.database import WorkoutDatabase
from src.utils import training_load as tl


def _weights(db_path, readings):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM daily_metrics WHERE metric_type = 'Weight Pounds'")
        for day, lb in readings:
            conn.execute("INSERT INTO daily_metrics (date, metric_type, metric_data) VALUES (?, 'Weight Pounds', ?)",
                         (day.isoformat(), json.dumps({"summary": {"avg": lb}})))
        conn.commit()
    finally:
        conn.close()


def test_wkg_uses_the_last_weeks_average_and_reports_the_gap_to_target():
    path = WorkoutDatabase().db_path
    today = date.today()
    # 12 weeks of 180 lb with a heavier outlier a month ago, then a week at 176 lb
    _weights(path, [(today - timedelta(days=d), 190.0 if d == 30 else 180.0) for d in range(8, 84)]
                   + [(today - timedelta(days=d), 176.0) for d in range(0, 7)])
    out = tl.power_to_weight(320, target=4.2, db_path=path)
    kg = 176 * 0.45359237
    assert out["weight_kg"] == round(kg, 1)                       # only the latest week counts
    assert out["wkg"] == round(320 / kg, 2)
    assert out["watts_needed"] == 16                              # 4.2 x 79.8 kg = 335.3 W, so 16 W more
    assert out["kg_to_lose"] == 3.6                               # or 79.8 -> 76.2 kg at the same FTP
    assert tl.power_to_weight(320, target=4.0, db_path=path)["watts_needed"] == 0   # already past 4.0
    assert len(out["weekly"]) >= 11 and out["weekly"][-1]["kg"] == round(kg, 1)


def test_wkg_needs_a_weight_and_an_ftp():
    path = WorkoutDatabase().db_path
    _weights(path, [])
    assert tl.power_to_weight(320, 4.0, path) == {}
    _weights(path, [(date.today(), 176.0)])
    assert tl.power_to_weight(None, 4.0, path) == {}


def test_the_target_comes_from_an_active_goal():
    path = WorkoutDatabase().db_path
    gid = goals.add_goal("Reach 4.2 W/kg by spring", category="performance")["id"]
    try:
        assert _wkg_target(path) == 4.2
    finally:
        goals.update_goal(gid, status="abandoned")
    assert "power_to_weight" in TestClient(app).get("/dashboard/trends").json()
