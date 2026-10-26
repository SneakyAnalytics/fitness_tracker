"""Best power per duration: this window vs the previous one, best ever, monthly trend, year-ago only when it exists."""
import sqlite3
from datetime import date

import pytest

from src.config import get_db_path
from src.storage.database import WorkoutDatabase
from src.utils.training_load import power_profile

TODAY = date(2026, 10, 26)


@pytest.fixture()
def conn():
    WorkoutDatabase()
    c = sqlite3.connect(get_db_path())
    c.execute("DELETE FROM ride_power_bests")
    c.commit()
    yield c
    c.close()


def ride(c, i, day, p5s=None, p1m=None, p5m=None, p20m=None, p60m=None):
    c.execute("INSERT INTO ride_power_bests (fit_file_id, ride_date, p5s, p1m, p5m, p20m, p60m) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (i, day, p5s, p1m, p5m, p20m, p60m))
    c.commit()


def by_key(profile):
    return {d["key"]: d for d in profile["durations"]}


def test_recent_vs_previous_window_best_ever_and_no_year_ago(conn):
    ride(conn, 1, "2025-12-01", p20m=330)                    # the best ever, long ago
    ride(conn, 2, "2026-06-10", p20m=280)                    # previous window (about 130 days back)
    ride(conn, 3, "2026-09-15", p20m=300, p5s=900)           # recent window
    ride(conn, 4, "2026-10-20", p20m=290)
    p = power_profile(as_of=TODAY)
    d = by_key(p)["p20m"]
    assert (d["recent"], d["prior"], d["change_pct"]) == (300, 280, 7.1)
    assert (d["best"], d["best_date"]) == (330, "2025-12-01")
    assert d["year_ago"] is None and d["year_ago_change_pct"] is None
    assert p["rides"] == {"recent": 2, "prior": 1, "year_ago": 0}
    assert by_key(p)["p5s"]["prior"] is None and by_key(p)["p5s"]["change_pct"] is None


def test_year_ago_appears_once_the_archive_reaches_back(conn):
    ride(conn, 1, "2025-10-20", p5m=400)
    ride(conn, 2, "2026-10-20", p5m=420)
    d = by_key(power_profile(as_of=TODAY))["p5m"]
    assert (d["year_ago"], d["year_ago_change_pct"]) == (400, 5.0)


def test_monthly_trend_covers_twelve_months_with_gaps(conn):
    ride(conn, 1, "2026-08-03", p1m=480)
    ride(conn, 2, "2026-08-20", p1m=500)
    ride(conn, 3, "2026-10-02", p1m=470)
    monthly = by_key(power_profile(as_of=TODAY))["p1m"]["monthly"]
    assert len(monthly) == 12 and monthly[0]["month"] == "2025-11" and monthly[-1]["month"] == "2026-10"
    by_month = {m["month"]: m["watts"] for m in monthly}
    assert by_month["2026-08"] == 500 and by_month["2026-09"] is None and by_month["2026-10"] == 470


def test_empty_archive_is_harmless(conn):
    p = power_profile(as_of=TODAY)
    assert p["archive_start"] is None and all(d["recent"] is None and d["best"] is None for d in p["durations"])
