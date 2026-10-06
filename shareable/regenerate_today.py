#!/usr/bin/env python3
"""Regenerate Zwift workouts for today with fresh news content"""
import os
import sys
from datetime import datetime, timedelta

# Add repo root to path
sys.path.insert(0, "/app")

from src.storage.database import WorkoutDatabase
from src.utils.zwift_workout_generator import generate_zwift_workouts_from_db

def main():
    # Get today's date
    today = datetime.now()
    start_date = today.strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=6)).strftime("%Y-%m-%d")
    
    print(f"Regenerating workouts for week: {start_date} to {end_date}")
    
    # Connect to database
    db = WorkoutDatabase()
    
    # Get week number from ISO calendar
    week_number = today.isocalendar()[1]
    
    # Generate workouts
    generated_files = generate_zwift_workouts_from_db(
        db_connection=db,
        start_date=start_date,
        end_date=end_date,
        ftp=258,
        output_dir="/app/shareable/zwift_workouts",
        week_number=week_number
    )
    
    print(f"\nGenerated {len(generated_files)} workout files:")
    for file_path in generated_files:
        print(f"  - {file_path}")
    
    print("\nDone!")

if __name__ == "__main__":
    main()
