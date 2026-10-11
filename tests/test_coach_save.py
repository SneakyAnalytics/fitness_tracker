"""Saving a plan runs in the background: building Zwift files (with news text) can
take longer than the browser waits, which showed 'timeout of 120000ms exceeded'
even though the save succeeded."""
import threading
import time

from fastapi.testclient import TestClient

from src.api import coach_routes
from src.api.app import app

client = TestClient(app)


class SlowSession:
    current_plan = {"startDate": "2026-10-12"}

    def __init__(self):
        self.release = threading.Event()

    def save_plan(self, zwift_dir):
        self.release.wait(5)
        return True, "Plan saved", ["a.zwo", "b.zwo"]


def test_save_returns_immediately_and_reports_when_done(monkeypatch):
    session = SlowSession()
    monkeypatch.setattr(coach_routes, "_session", lambda week, model="CLAUDE_OPUS": session)
    coach_routes._saves.clear()

    first = client.post("/coach/session/save", json={"week_start": "2026-10-05"}).json()
    assert first["state"] == "running"
    again = client.post("/coach/session/save", json={"week_start": "2026-10-05"}).json()
    assert again["state"] == "running"  # a second click doesn't start a second save

    session.release.set()
    for _ in range(50):
        status = client.get("/coach/session/save", params={"week_start": "2026-10-07"}).json()
        if status["state"] != "running":
            break
        time.sleep(0.05)
    assert status == {"state": "done", "message": "Plan saved", "zwift_files": ["a.zwo", "b.zwo"]}
