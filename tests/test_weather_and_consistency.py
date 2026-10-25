"""Calendar weather proxy and the dashboard's consistency ribbon."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from src.api import coach_routes
from src.api.app import app
from src.api.coach_routes import week_status

client = TestClient(app)


def test_week_status_uses_a_15_percent_band():
    assert week_status(500, 430, 510) == "hit"
    assert week_status(380, 430, 510) == "hit"      # 430 * .85 = 365.5
    assert week_status(360, 430, 510) == "miss"
    assert week_status(600, 430, 510) == "miss"     # 510 * 1.15 = 586.5
    assert week_status(500, None, None) == "none"   # a week with no saved plan


def test_weather_is_filtered_cached_and_quiet_on_failure(monkeypatch):
    calls = []
    today = date.today()
    days = [(today + timedelta(days=i)).isoformat() for i in range(4)]

    def fake_forecast(lat, lon):
        calls.append((lat, lon))
        return {"daily": {"time": days, "weather_code": [0, 61, 3, 95],
                          "temperature_2m_max": [70, 55, 60, 50], "temperature_2m_min": [50, 45, 44, 40],
                          "precipitation_probability_max": [0, 80, 10, 90]}}

    coach_routes._weather_cache.clear()
    monkeypatch.setattr(coach_routes, "_fetch_forecast", fake_forecast)
    got = client.get("/weather", params={"start": days[1], "end": days[2]}).json()["days"]
    assert sorted(got) == days[1:3] and got[days[1]]["rain_pct"] == 80
    client.get("/weather", params={"start": days[0], "end": days[3]})
    assert len(calls) == 1                           # second request served from the cache

    coach_routes._weather_cache.clear()
    monkeypatch.setattr(coach_routes, "_fetch_forecast", lambda *a: (_ for _ in ()).throw(RuntimeError("down")))
    assert client.get("/weather", params={"start": days[0], "end": days[3]}).json() == {"days": {}}
