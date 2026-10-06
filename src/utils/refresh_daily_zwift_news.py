import os
import json
import re
from datetime import date
from typing import Optional

from ..storage.database import WorkoutDatabase
from .zwift_workout_generator import generate_zwift_workouts_from_db


def _extract_ftp(db: WorkoutDatabase, start_date: str, end_date: str, fallback: int = 302) -> int:
    """
    Extract FTP value with priority:
    1. Athlete settings (primary source)
    2. Weekly plan FTP
    3. Weekly plan notes
    4. Fallback (302W default)
    """
    extracted_ftp = fallback
    
    # First, try to get FTP from athlete settings (primary source)
    try:
        athlete_settings = db.get_athlete_settings('default')
        if athlete_settings and athlete_settings.get('ftp'):
            extracted_ftp = athlete_settings['ftp']
            print(f"DEBUG: Using FTP from athlete settings: {extracted_ftp}W")
            return extracted_ftp
    except Exception as e:
        print(f"Could not load athlete settings for FTP: {e}")
    
    # Fallback to weekly plan FTP
    try:
        proposed_workouts_data = db.get_proposed_workouts_for_week(start_date, end_date)
        weekly_plan = proposed_workouts_data.get('weekly_plan', {})
        if weekly_plan and weekly_plan.get('ftp'):
            extracted_ftp = weekly_plan.get('ftp')
            print(f"DEBUG: Using FTP from weekly plan: {extracted_ftp}W")
        elif weekly_plan and weekly_plan.get('notes'):
            notes = weekly_plan['notes']
            notes_data = json.loads(notes) if isinstance(notes, str) else notes
            if isinstance(notes_data, dict):
                special_considerations = notes_data.get('specialConsiderations', '')
                ftp_match = re.search(r'FTP[:\s]*(\d+)W?', special_considerations, re.IGNORECASE)
                if ftp_match:
                    extracted_ftp = int(ftp_match.group(1))
                    print(f"DEBUG: Using FTP from weekly plan notes: {extracted_ftp}W")
    except Exception as e:
        print(f"Could not extract FTP from weekly plan: {e}, using fallback {extracted_ftp}W")
    
    return extracted_ftp


def plan_week_number(db: WorkoutDatabase, target_date: str) -> Optional[int]:
    """Week number of the saved plan containing target_date (matches Week_<n> folders)."""
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    try:
        row = conn.execute("SELECT weekNumber FROM daily_plans WHERE date = ? ORDER BY id DESC LIMIT 1",
                           (target_date,)).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def refresh_daily_zwift_news(target_date: Optional[str] = None) -> list[str]:
    """Regenerate today's Zwift files so text events use fresh news."""
    if target_date is None:
        target_date = date.today().isoformat()

    output_dir = os.getenv('ZWIFT_WORKOUTS_DIR', "~/Documents/Zwift/Workouts/6870291")
    db = WorkoutDatabase()
    ftp = _extract_ftp(db, target_date, target_date)

    print(f"Refreshing Zwift workouts for {target_date} using FTP {ftp}W")
    return generate_zwift_workouts_from_db(
        db_connection=db,
        start_date=target_date,
        end_date=target_date,
        ftp=ftp,
        output_dir=output_dir,
        # Same Week_<n> folder the plan was saved to (not the calendar week).
        week_number=plan_week_number(db, target_date),
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", dest="date", help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--week-dir", action="store_true",
                        help="only print the Week_<n> folder for the date (used by the Beelink sync task)")
    args = parser.parse_args()

    if args.week_dir:
        n = plan_week_number(WorkoutDatabase(), args.date or date.today().isoformat())
        print(f"Week_{n}" if n else "")
    else:
        files = refresh_daily_zwift_news(args.date)
        print(f"Generated {len(files)} file(s):")
        for path in files:
            print(f"- {path}")
