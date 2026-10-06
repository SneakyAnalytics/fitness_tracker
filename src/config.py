"""Shared runtime configuration."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_db_path() -> str:
    """Path to the SQLite database.

    Override with FITNESS_DB_PATH (tests point this at a temp copy so they never
    touch the real database).
    """
    return os.getenv("FITNESS_DB_PATH") or str(PROJECT_ROOT / "data" / "fitness_data.db")
