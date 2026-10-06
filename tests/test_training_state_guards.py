from datetime import date, timedelta

from fastapi.testclient import TestClient

from src.api.app import app
from src.utils.training_load import compute_load_series


def test_load_series_never_projects_past_today():
    today = date.today()
    series = compute_load_series({today - timedelta(days=3): 100.0}, end=today + timedelta(days=10))
    assert series[-1]["date"] == today.isoformat()


def test_recap_cannot_start_before_the_week_is_over():
    monday = date.today() - timedelta(days=date.today().weekday())
    if monday + timedelta(days=6) == date.today():
        monday += timedelta(days=7)  # on a Sunday this week is allowed; use next week
    r = TestClient(app).post("/coach/session/begin", json={"week_start": monday.isoformat()})
    assert r.status_code == 400
    assert "isn't over yet" in r.json()["detail"]
