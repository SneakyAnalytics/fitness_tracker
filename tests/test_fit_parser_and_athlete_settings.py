import json
from fastapi.testclient import TestClient
from src.api.app import app
from src.utils.fit_parser import FitParser

client = TestClient(app)


def test_fitparser_hr_zones_env_override():
    fp = FitParser()
    # Provide sample HR data
    hr_data = [120, 130, 140, 150, 160, 170, 180]
    # Set env override (simulate 5 upper bounds)
    import os
    os.environ['ATHLETE_HR_ZONES'] = '130,145,160,175,200'
    zones = fp.calculate_hr_zones(hr_data, max_hr=200)
    assert isinstance(zones, dict)
    # Check that zone names map to percentages and sum approx 100
    total = sum(z for z in zones.values())
    assert abs(total - 100.0) < 1e-6 or total == 0.0


def test_athlete_settings_endpoints():
    # Ensure GET returns empty for default initially
    r = client.get('/athlete/settings')
    assert r.status_code == 200
    data = r.json()
    assert data.get('athlete_id') == 'default'

    # Save settings
    settings = {"ftp": 300, "hr_zones": "138,156,165,173,200", "power_zones": [165,225,270,315,9999]}
    r2 = client.post('/athlete/settings', data={"athlete_id": 'default', "settings": json.dumps(settings)})
    assert r2.status_code == 200
    r3 = client.get('/athlete/settings')
    assert r3.status_code == 200
    loaded = r3.json().get('settings', {})
    # Check at least ftp persisted
    assert loaded.get('ftp') == 300 or str(loaded.get('ftp')) == '300'
