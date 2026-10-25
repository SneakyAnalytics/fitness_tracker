"""The dashboard's Achievements strip: completed goals as medals plus the next dated target."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from src.api.app import app
from src.storage.database import WorkoutDatabase
from src.storage import goals

client = TestClient(app)


def test_trends_carry_medals_and_the_next_target():
    db = WorkoutDatabase()
    soon = (date.today() + timedelta(days=9)).isoformat()
    later = (date.today() + timedelta(days=40)).isoformat()
    a = goals.add_goal("Complete the century", category="event", target_date="2026-09-12")["id"]
    b = goals.add_goal("Ramp test", category="event", target_date="2026-10-20")["id"]
    goals.add_goal("Zwift league", category="event", target_date=later)
    goals.add_goal("Race the crit", category="event", target_date=soon)
    goals.update_goal(a, status="completed")
    goals.update_goal(b, status="completed")
    out = client.get("/dashboard/trends").json()["goals"]
    done = [g["description"] for g in out["completed"]]
    assert done.index("Ramp test") < done.index("Complete the century")        # newest first
    assert out["next"]["description"] == "Race the crit"                       # soonest active target
    assert out["next"]["days_until"] == 9
