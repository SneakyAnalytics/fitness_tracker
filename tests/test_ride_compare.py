"""Compare page: smoothed series and the two ride endpoints."""
import json
import sqlite3

from fastapi.testclient import TestClient

from src.api.app import app
from src.storage.database import WorkoutDatabase
from src.utils.ride_compare import resample, ride_series, smooth

client = TestClient(app)


def test_smoothing_skips_gaps_and_resampling_averages_blocks():
    assert smooth([100, 200, 300], 2) == [100, 150, 250]
    assert smooth([100, None, 300], 3) == [100, 100, 200]
    assert smooth([None, None], 2) == [None, None]
    assert resample([10, 20, 30, 40, 50], 2) == [15, 35, 50]
    assert resample([None, None, 8], 2) == [None, 8]


def test_ride_series_reports_summary_and_one_point_per_step():
    fit = {"duration_seconds": 60,
           "power_metrics": {"average_power": 200.4, "normalized_power": 215.6, "intensity_factor": 0.7234, "tss": 45.55,
                             "power_series": [200] * 30 + [300] * 30},
           "hr_metrics": {"average_hr": 140.2, "max_hr": 171, "hr_series": [140] * 60}}
    out = ride_series(fit, step=10, smooth_window=1)
    assert out["power"] == [200, 200, 200, 300, 300, 300] and out["hr"] == [140] * 6
    assert out["summary"]["np"] == 216 and out["summary"]["intensity_factor"] == 0.72 and out["summary"]["tss"] == 45.5
    assert ride_series({}, step=10)["power"] == []


def test_ride_endpoints_list_and_return_a_series():
    path = WorkoutDatabase().db_path
    conn = sqlite3.connect(path)
    try:
        fit = {"duration_seconds": 40, "power_metrics": {"average_power": 150, "power_series": [150] * 40},
               "hr_metrics": {"average_hr": 120, "hr_series": [120] * 40}}
        conn.execute("INSERT INTO fit_files (file_name, workout_day, workout_title, fit_data) VALUES ('c.fit','2026-04-01','Ride',?)",
                     (json.dumps(fit),))
        fid = conn.execute("SELECT id FROM fit_files WHERE file_name = 'c.fit'").fetchone()[0]
        cur = conn.execute("INSERT INTO workouts (workout_day, workout_title, workout_data, fit_file_id) VALUES ('2026-04-01','Compare me',?,?)",
                           (json.dumps({"metrics": {"actual_tss": 33, "actual_duration": 40}}), fid))
        wid = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    listed = client.get("/compare/rides").json()["rides"]
    mine = [r for r in listed if r["id"] == wid][0]
    assert mine["name"] == "Compare me" and mine["tss"] == 33
    got = client.get(f"/compare/rides/{wid}", params={"step": 10, "smooth": 1}).json()
    assert got["power"] == [150] * 4 and got["hr"] == [120] * 4 and got["intervals"] == []
    assert client.get("/compare/rides/999999").status_code == 404
