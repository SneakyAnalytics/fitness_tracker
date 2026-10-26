"""Zwift's FTP: a ramp test is a changepoint, and a confirmed value stands until rides clearly disagree.

Real case (Oct 2026): rides before the Oct 20 ramp test implied ~305 W, the one after implied 320 W, and
the dashboard showed 314 W because it took the median of the last three rides across the test.
"""
import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.config import get_db_path
from src.storage.database import WorkoutDatabase
from src.utils import zwift_ftp

client = TestClient(app)
TODAY = date(2026, 10, 26)


@pytest.fixture()
def db():
    WorkoutDatabase()
    conn = sqlite3.connect(get_db_path())
    for t in ("zwift_ftp_observations", "workouts"):
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    WorkoutDatabase().save_athlete_settings("default", {"ftp": 306})
    yield conn
    conn.close()


def observe(conn, rows):
    for i, (day, ftp) in enumerate(rows, start=1000):
        conn.execute("INSERT INTO zwift_ftp_observations (workout_id, ride_date, ftp, intervals_used) VALUES (?, ?, ?, 4)", (i, day, ftp))
    conn.commit()


def ramp_test(conn, day):
    conn.execute("INSERT INTO workouts (workout_day, workout_title, workout_data, sequence_number) VALUES (?, 'Zwift - FTP Ramp Test', '{}', 1)", (day,))
    conn.commit()


PRE_TEST = [("2026-10-12", 306), ("2026-10-13", 306), ("2026-10-14", 305), ("2026-10-16", 314), ("2026-10-19", 305)]


def test_rides_before_a_test_are_not_averaged_with_rides_after_it(db):
    observe(db, PRE_TEST + [("2026-10-25", 320)])
    ramp_test(db, "2026-10-20")
    now = zwift_ftp.current(today=TODAY)
    assert now["ftp"] == 320 and now["source"] == "rides_since_test"
    assert now["changed_on"] == "2026-10-20"
    assert now["weeks_since_change"] < 1 and not now["test_due"]


def test_before_any_ride_after_the_test_the_old_ftp_is_kept(db):
    observe(db, PRE_TEST)
    ramp_test(db, "2026-10-20")
    assert zwift_ftp.current(today=TODAY)["ftp"] == 305   # median of the last three rides before the test (305, 314, 305)


def test_a_confirmed_ftp_stands_over_rounding_noise(db):
    observe(db, PRE_TEST + [("2026-10-25", 320)])
    ramp_test(db, "2026-10-20")
    result = zwift_ftp.confirm_ftp(321, "2026-10-20")
    assert result["ftp"] == 321 and result["source"] == "confirmed" and result["changed_on"] == "2026-10-20"
    assert WorkoutDatabase().get_athlete_settings()["ftp"] == 321        # the app's FTP follows


def test_confirmation_yields_when_later_rides_all_disagree(db):
    observe(db, PRE_TEST + [("2026-10-25", 320), ("2026-11-01", 330), ("2026-11-03", 331)])
    ramp_test(db, "2026-10-20")
    zwift_ftp.confirm_ftp(321, "2026-10-20")
    now = zwift_ftp.current(today=date(2026, 11, 4))
    assert now["ftp"] == 330 and now["source"] == "rides"


def test_a_newer_test_supersedes_an_old_confirmation(db):
    observe(db, [("2026-10-25", 320), ("2026-12-10", 335)])
    ramp_test(db, "2026-10-20")
    zwift_ftp.confirm_ftp(321, "2026-10-20")
    ramp_test(db, "2026-12-05")
    assert zwift_ftp.current(today=date(2026, 12, 12))["ftp"] == 335


def test_confirm_validates_and_the_profile_form_cannot_wipe_it(db):
    with pytest.raises(ValueError):
        zwift_ftp.confirm_ftp(50)
    with pytest.raises(ValueError):
        zwift_ftp.confirm_ftp(320, "2999-01-01")
    assert client.post("/zwift_ftp/confirm", json={"ftp": 321, "date": "2026-10-20"}).json()["ftp"] == 321
    client.post("/athlete/settings", json={"settings": {"ftp": 321, "hr_zones": "138,156"}})   # a form that never heard of the key
    assert zwift_ftp.confirmed_ftp()["ftp"] == 321
    assert client.post("/zwift_ftp/confirm", json={"ftp": 20}).status_code == 422
