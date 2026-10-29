"""Exercise demonstrations from the open Free Exercise DB (public domain: github.com/yuhonas/free-exercise-db).

Google offers no image API and scraping it breaks (and breaks its terms), so Gym mode matches each exercise name
to this dataset of ~870 movements, two photos each, and shows the closest match with its written steps. The
index and the images are cached on the data volume, so after the first lookup nothing is fetched twice.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from src.config import get_db_path

BASE = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main"
INDEX_URL = f"{BASE}/dist/exercises.json"
INDEX_MAX_AGE = 30 * 86400
MIN_SCORE = 0.7

_STOP = {"the", "a", "an", "of", "on", "to", "and", "your", "bodyweight", "body", "weight", "double", "hold", "series", "circuit"}
_index_cache: Optional[List[Dict[str, Any]]] = None


def cache_dir() -> Path:
    d = Path(get_db_path()).parent / "exercise_library"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _clean(name: str) -> str:
    """"Side Plank (Left)" -> "side plank"; "Pallof Press (or Banded Rotation Hold)" -> "pallof press"; drops "each side"."""
    name = re.sub(r"\(.*?\)", " ", (name or "").lower())
    name = re.split(r"\bor\b| / ", name)[0]
    name = re.sub(r"\b(each|per)\s+(side|leg|arm|direction)\b", " ", name)
    return name.replace("-", " ")


def _stem(t: str) -> str:
    return t[:-1] if len(t) > 3 and t.endswith("s") else t       # raises ~ raise


def tokens(name: str) -> set:
    return {_stem(t) for t in re.split(r"[^a-z0-9]+", _clean(name)) if t and t not in _STOP}


def _squash(name: str) -> str:
    return _stem(re.sub(r"[^a-z0-9]", "", _clean(name)))


def score(query: str, candidate: str) -> float:
    """1.0 for the same words however spaced ("Push-Ups" = "Pushups"), otherwise the overlap (Jaccard) of their words.

    Plain overlap is deliberate: a candidate with an extra distinguishing word ("Side Bridge" for "Glute Bridge",
    "Handstand Push-Ups" for "Push-Ups") must score low, because a wrong demonstration is worse than none.
    """
    if _squash(query) and _squash(query) == _squash(candidate):
        return 1.0
    a, b = tokens(query), tokens(candidate)
    return len(a & b) / len(a | b) if a and b else 0.0


# Hand-checked pairs where the library has the same movement under another name (mostly stretches, which people
# write many ways). Keys are the cleaned name (no brackets, lower case); values are the library's exact names. Yoga poses
# the library lacks (pigeon, downward dog, legs up the wall, open book) are deliberately absent: a near miss would be a
# wrong demonstration.
ALIASES = {
    "cat cow": "Cat Stretch",
    "soleus wall stretch": "Standing Soleus And Achilles Stretch",
    "standing soleus stretch": "Standing Soleus And Achilles Stretch",
    "standing calf stretch": "Standing Gastrocnemius Calf Stretch",
    "supine hamstring strap stretch": "Leg-Up Hamstring Stretch",
    "seated forward fold": "Seated Floor Hamstring Stretch",
    "kneeling hip flexor lunge": "Kneeling Hip Flexor",
    "low lunge hip flexor stretch": "Kneeling Hip Flexor",
    "half kneeling hip flexor stretch": "Kneeling Hip Flexor",
    "hip flexor kneeling stretch": "Kneeling Hip Flexor",
    "ankle circles and alphabet": "Ankle Circles",
    "standing quad stretch": "Quad Stretch",
}


def _alias_key(name: str) -> str:
    return re.sub(r"\s+", " ", _clean(name).strip())


def best_match(name: str, index: List[Dict[str, Any]], min_score: float = MIN_SCORE) -> Optional[Dict[str, Any]]:
    wanted = ALIASES.get(_alias_key(name))
    if wanted:
        for ex in index:
            if ex["name"] == wanted and ex.get("images"):
                return {**ex, "score": 1.0}
    best, best_score = None, 0.0
    for ex in index:
        if not ex.get("images"):
            continue
        s = score(name, ex["name"])
        if s > best_score:
            best, best_score = ex, s
    return {**best, "score": round(best_score, 2)} if best and best_score >= min_score else None


def load_index(refresh: bool = False) -> List[Dict[str, Any]]:
    """The dataset, from the volume cache when it is fresh; a stale cache beats nothing if GitHub is unreachable."""
    global _index_cache
    path = cache_dir() / "exercises.json"
    fresh = path.exists() and time.time() - path.stat().st_mtime < INDEX_MAX_AGE
    if _index_cache is not None and not refresh and fresh:
        return _index_cache
    if refresh or not fresh:
        try:
            r = requests.get(INDEX_URL, timeout=20)
            r.raise_for_status()
            data = r.json()
            path.write_text(json.dumps(data))
        except (requests.RequestException, ValueError):
            if not path.exists():
                return []
    _index_cache = json.loads(path.read_text())
    return _index_cache


SAFE_ID = re.compile(r"^[A-Za-z0-9_\-]{1,120}$")


def image_path(exercise_id: str, n: int) -> Optional[Path]:
    """Local file for one photo, downloading it the first time. None if it doesn't exist upstream."""
    if not SAFE_ID.match(exercise_id) or not 0 <= n <= 9:
        return None
    path = cache_dir() / f"{exercise_id}-{n}.jpg"
    if path.exists():
        return path
    try:
        r = requests.get(f"{BASE}/exercises/{exercise_id}/{n}.jpg", timeout=20)
    except requests.RequestException:
        return None
    if r.status_code != 200 or not r.content:
        return None
    path.write_bytes(r.content)
    return path
