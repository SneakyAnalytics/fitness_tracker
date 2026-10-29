"""Exercise demonstrations: matching names to the open library, and the cached image route."""
from fastapi.testclient import TestClient

from src.api.app import app
from src.utils import exercise_library as lib

client = TestClient(app)

INDEX = [{"id": "Cat_Stretch", "name": "Cat Stretch", "images": ["c/0.jpg"]},
         {"id": "Kneeling_Hip_Flexor", "name": "Kneeling Hip Flexor", "images": ["k/0.jpg"]},
         {"id": "Goblet_Squat", "name": "Goblet Squat", "images": ["Goblet_Squat/0.jpg", "Goblet_Squat/1.jpg"],
          "instructions": ["Hold the weight at your chest."], "primaryMuscles": ["quadriceps"], "secondaryMuscles": ["glutes"]},
         {"id": "Pushups", "name": "Pushups", "images": ["Pushups/0.jpg"]},
         {"id": "Handstand_Push-Ups", "name": "Handstand Push-Ups", "images": ["x/0.jpg"]},
         {"id": "Side_Bridge", "name": "Side Bridge", "images": ["y/0.jpg"]},
         {"id": "Plank", "name": "Plank", "images": ["p/0.jpg"]},
         {"id": "Standing_Calf_Raises", "name": "Standing Calf Raises", "images": ["c/0.jpg"]},
         {"id": "Hip_Hamstring", "name": "90/90 Hamstring", "images": ["h/0.jpg"]},
         {"id": "NoPhotos", "name": "Bear Crawl", "images": []}]


def test_matching_is_generous_about_wording_and_strict_about_the_movement():
    m = lambda n: (lib.best_match(n, INDEX) or {}).get("id")          # noqa: E731
    assert m("Goblet Squats") == "Goblet_Squat" and m("goblet-squat") == "Goblet_Squat"
    assert m("Push-Ups") == "Pushups"                                  # same word, different spacing
    assert m("Standing Double-Leg Calf Raise") == "Standing_Calf_Raises"
    assert m("Plank Hold") == "Plank" and m("Side Plank (Left)") is None      # a side plank is not a plank
    assert m("Glute Bridge") is None                                   # "Side Bridge" is a different movement
    assert m("90/90 Hip Switches") is None                             # the "/" inside 90/90 isn't an alternative
    assert m("Goblet Squat or Barbell Back Squat") == "Goblet_Squat"   # first alternative
    assert m("Bear Crawl") is None                                      # no photos, no match
    assert lib.score("Dead Bugs", "Dead Bug") == 1.0


def test_match_route_returns_photo_paths_and_steps(monkeypatch):
    monkeypatch.setattr(lib, "load_index", lambda refresh=False: INDEX)
    got = client.get("/exercise/match", params={"name": "Goblet Squats"}).json()["match"]
    assert got["name"] == "Goblet Squat" and got["images"] == ["exercise/image/Goblet_Squat/0", "exercise/image/Goblet_Squat/1"]
    assert got["steps"] == ["Hold the weight at your chest."] and set(got["muscles"]) == {"quadriceps", "glutes"}
    assert client.get("/exercise/match", params={"name": "Something Unheard Of"}).json() == {"match": None}


def test_image_route_downloads_once_and_rejects_bad_ids(monkeypatch, tmp_path):
    monkeypatch.setattr(lib, "cache_dir", lambda: tmp_path)
    calls = []

    class Resp:
        status_code, content = 200, b"\xff\xd8jpeg"

    monkeypatch.setattr(lib.requests, "get", lambda url, timeout: calls.append(url) or Resp())
    first = client.get("/exercise/image/Goblet_Squat/0")
    again = client.get("/exercise/image/Goblet_Squat/0")
    assert first.status_code == again.status_code == 200 and first.content == b"\xff\xd8jpeg"
    assert len(calls) == 1 and calls[0].endswith("/exercises/Goblet_Squat/0.jpg")      # second hit came from the cache
    assert client.get("/exercise/image/..%2F..%2Fetc/0").status_code == 404
    assert client.get("/exercise/image/Goblet_Squat/99").status_code == 404


def test_hand_checked_aliases_cover_stretch_names_but_yoga_poses_the_library_lacks_stay_unmatched():
    m = lambda n: (lib.best_match(n, INDEX) or {}).get("id")          # noqa: E731
    assert m("Cat-Cow") == "Cat_Stretch" and m("Cat-Cow (Spinal Mobility)") == "Cat_Stretch"
    assert m("Low Lunge Hip Flexor Stretch") == "Kneeling_Hip_Flexor" and m("Kneeling Hip Flexor Lunge") == "Kneeling_Hip_Flexor"
    assert m("Half Pigeon Pose") is None and m("Downward Dog") is None and m("Legs Up the Wall") is None
    for alias, target in lib.ALIASES.items():                         # every alias must point at something real
        assert target and alias == alias.lower()
