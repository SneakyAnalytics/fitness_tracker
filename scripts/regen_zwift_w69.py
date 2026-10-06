#!/usr/bin/env python3
"""Regenerate all .zwo files for Week_69 (2026-03-09 to 2026-03-15)."""
import sys, os
sys.path.insert(0, '/app/src')

from utils.zwift_workout_generator import generate_zwift_workouts_from_db
from storage.database import WorkoutDatabase

db = WorkoutDatabase()
ZWIFT_DIR = os.getenv('ZWIFT_WORKOUTS_DIR', '/app/shareable/zwift_workouts')
START = '2026-03-09'
END   = '2026-03-15'
FTP   = 305

print(f"Generating Zwift files for {START} to {END}, FTP={FTP}W, dir={ZWIFT_DIR}")
files = generate_zwift_workouts_from_db(
    db_connection=db,
    start_date=START,
    end_date=END,
    ftp=FTP,
    output_dir=ZWIFT_DIR,
    week_number=69,
)
print(f"\n✅ Generated {len(files)} files:")
for f in files:
    print(f"  {os.path.basename(f)}")
