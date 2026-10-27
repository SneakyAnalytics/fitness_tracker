"""Exercise demonstrations for Gym mode (see utils/exercise_library)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.utils import exercise_library as lib

router = APIRouter(prefix="/exercise")


@router.get("/match")
def match(name: str):
    """The closest exercise in the open library, with photo paths and written steps; `match` is null if none is close."""
    found = lib.best_match(name, lib.load_index())
    if not found:
        return {"match": None}
    return {"match": {
        "id": found["id"], "name": found["name"], "score": found["score"],
        "images": [f"exercise/image/{found['id']}/{i}" for i in range(len(found["images"]))],
        "steps": found.get("instructions") or [],
        "muscles": (found.get("primaryMuscles") or []) + (found.get("secondaryMuscles") or []),
        "source": "Free Exercise DB (public domain)",
    }}


@router.get("/image/{exercise_id}/{n}")
def image(exercise_id: str, n: int):
    path = lib.image_path(exercise_id, n)
    if not path:
        raise HTTPException(status_code=404, detail="no such image")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=2592000"})
