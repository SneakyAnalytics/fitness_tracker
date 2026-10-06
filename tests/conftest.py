"""Test isolation: never let tests touch data/fitness_data.db.

This runs before test modules are imported, so module-level objects such as
`TestClient(app)` already see the temp database.
"""
import os
import tempfile
from pathlib import Path

_tmp_dir = Path(tempfile.mkdtemp(prefix="fitness_tests_"))
os.environ["FITNESS_DB_PATH"] = str(_tmp_dir / "test_fitness_data.db")


import pytest


@pytest.fixture(scope="session", autouse=True)
def _initialized_test_db():
    """Create the schema (base tables + migrations) in the temp DB once."""
    from src.storage.database import WorkoutDatabase
    WorkoutDatabase()
