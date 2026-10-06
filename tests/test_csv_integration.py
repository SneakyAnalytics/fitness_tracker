import io
import os
import shutil
import sqlite3
import pandas as pd
import pytest
from pathlib import Path

from src.storage.database import WorkoutDatabase
from src.utils.helpers import clean_float, clean_workout_data


def _load_csv(csv_path: Path) -> pd.DataFrame:
    with open(csv_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    df = pd.read_csv(io.StringIO(raw))
    # CSV from upstream is date-only (YYYY-MM-DD)
    df['WorkoutDay'] = pd.to_datetime(df['WorkoutDay'], errors='coerce').dt.strftime('%Y-%m-%d')
    return df


@pytest.mark.integration
def test_csv_upload_and_weekly_summary(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    csv_path = repo_root / 'workouts 2.csv'
    if not csv_path.exists():
        pytest.skip(f"fixture CSV not present at {csv_path}")

    df = _load_csv(csv_path)
    assert len(df) == 7

    # Copy the real DB to a temp location so tests can run without mutating the user's DB
    src_db = repo_root / 'data' / 'fitness_data.db'
    assert src_db.exists(), f"Source DB not found at {src_db}"
    tmp_db = tmp_path / 'fitness_data_test.db'
    shutil.copy(src_db, tmp_db)

    db = WorkoutDatabase(str(tmp_db))

    min_date = df['WorkoutDay'].min()
    max_date = df['WorkoutDay'].max()

    # Clean any existing workouts in range and then save CSV rows through the same code path
    conn = sqlite3.connect(db.db_path)
    cur = conn.cursor()
    cur.execute('DELETE FROM workouts WHERE workout_day >= ? AND workout_day <= ?', (min_date, max_date))
    conn.commit()
    conn.close()

    saved = 0
    for _, row in df.iterrows():
        actual_duration = None
        t = row.get('TimeTotalInHours')
        if pd.notna(t):
            actual_duration = clean_float(t * 60)

        workout = {
            'title': str(row['Title']).strip() if pd.notna(row.get('Title')) else '',
            'type': str(row['WorkoutType']).strip() if pd.notna(row.get('WorkoutType')) else '',
            'workout_day': str(row['WorkoutDay']).strip(),
            'metrics': {
                'actual_tss': float(row['TSS']) if pd.notna(row.get('TSS')) else None,
                'actual_duration': actual_duration,
                'rpe': float(row['Rpe']) if pd.notna(row.get('Rpe')) else None,
            },
            'power_data': {
                'average': float(row['PowerAverage']) if pd.notna(row.get('PowerAverage')) else None,
                'max': float(row['PowerMax']) if pd.notna(row.get('PowerMax')) else None,
                'if': float(row['IF']) if pd.notna(row.get('IF')) else None,
            } if pd.notna(row.get('PowerAverage')) else None,
            'heart_rate_data': None,
            'athlete_comments': str(row.get('AthleteComments')) if pd.notna(row.get('AthleteComments')) else None
        }
        cleaned = clean_workout_data(workout)
        ok = db.save_workout(cleaned)
        if ok:
            saved += 1

    assert saved == 7

    # Run weekly summary to exercise FIT selection
    summary = db.generate_weekly_summary(min_date, max_date)
    assert summary is not None, 'generate_weekly_summary returned None'
    sessions = summary.get('sessions_completed', 0)
    assert sessions >= 7

    # Verify workouts exist in DB and check fit_file_id logic for power vs no-power days
    conn = sqlite3.connect(db.db_path)
    cur = conn.cursor()
    cur.execute("SELECT workout_day, fit_file_id FROM workouts WHERE workout_day BETWEEN ? AND ? ORDER BY workout_day", (min_date, max_date))
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 7

    # Map workout_day -> fit_file_id
    mapping = {r[0]: r[1] for r in rows}

    # Days with power in the CSV should have a fit_file_id (or at least the code attempted matching)
    power_days = ['2025-10-27', '2025-10-29', '2025-10-30', '2025-11-01', '2025-11-02']
    for d in power_days:
        assert d in mapping
        assert mapping[d] is not None, f"Expected fit_file_id for {d} to be set (power day)"

    # The lab day 2025-10-28 had no power data; expect fit_file_id to be None
    assert mapping.get('2025-10-28') is None
