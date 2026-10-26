"""The readiness chart's data: a daily series with a baseline and band per metric."""
import json
import sqlite3
from datetime import date, timedelta

import pytest

from src.config import get_db_path
from src.storage.database import WorkoutDatabase
from src.utils.training_load import readiness_series

TODAY = date(2026, 10, 26)


@pytest.fixture()
def conn():
    WorkoutDatabase()
    c = sqlite3.connect(get_db_path())
    c.execute("DELETE FROM daily_metrics")
    c.commit()
    yield c
    c.close()


def put(c, day, metric, value):
    data = json.dumps({"summary": {"avg": value, "max": value, "min": value}})
    c.execute("INSERT INTO daily_metrics (date, metric_type, metric_data) VALUES (?, ?, ?)", (day, metric, data))
    c.commit()


def test_series_baseline_and_bands(conn):
    for i in range(30):
        day = (TODAY - timedelta(days=i)).isoformat()
        put(conn, day, "HRV", 60 + (i % 3))                      # baseline 61
        put(conn, day, "Pulse", 46)
        put(conn, day, "Sleep Hours", 7.5)
    out = readiness_series(days=30, as_of=TODAY)
    assert len(out["days"]) == 30 and out["days"][0]["date"] < out["days"][-1]["date"]
    hrv = out["baselines"]["hrv"]
    assert hrv["baseline"] == 61.0 and (hrv["low"], hrv["high"]) == (54.9, 67.1)
    assert out["baselines"]["resting_hr"]["baseline"] == 46.0
    assert out["baselines"]["sleep_hours"]["target"] == 7.0 and out["baselines"]["sleep_hours"]["low"] is None


def test_todays_partial_sleep_is_dropped_but_a_real_night_is_kept(conn):
    put(conn, "2026-10-24", "Sleep Hours", 8.1)
    put(conn, "2026-10-26", "Sleep Hours", 2.0)                  # still being recorded
    days = {p["date"]: p for p in readiness_series(days=7, as_of=TODAY)["days"]}
    assert days["2026-10-24"]["sleep_hours"] == 8.1 and "2026-10-26" not in days


def test_gaps_and_an_empty_history_are_harmless(conn):
    assert readiness_series(as_of=TODAY) == {"days": [], "baselines": {}, "window_days": 90}
    put(conn, "2026-10-20", "HRV", 58)
    out = readiness_series(days=30, as_of=TODAY)
    assert out["days"] == [{"date": "2026-10-20", "hrv": 58.0}] and "resting_hr" not in out["baselines"]
