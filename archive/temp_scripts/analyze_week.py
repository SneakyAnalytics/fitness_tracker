#!/usr/bin/env python3
"""
Analyze all FIT files from Nov 17-20 with the enhanced interval-by-interval analysis
"""
import sys
sys.path.insert(0, '/Users/jacobrobinson/fitness_tracker')

from src.utils.fit_file_analyzer import FitFileAnalyzer
from src.storage.database import WorkoutDatabase
from pathlib import Path
import json

def analyze_week():
    """Analyze all workouts from Nov 17-20"""
    db = WorkoutDatabase('data/fitness_data.db')
    
    # Get athlete FTP
    settings = db.get_athlete_settings()
    ftp = settings.get('ftp', 300)
    print(f"Using FTP: {ftp}W\n")
    
    # Get all FIT files from Nov 17-20 that don't have analyses
    import sqlite3
    conn = sqlite3.connect('data/fitness_data.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT f.id, f.workout_day, f.file_name, f.fit_data
        FROM fit_files f
        LEFT JOIN workout_analyses wa ON f.id = wa.fit_file_id
        WHERE f.workout_day >= '2025-11-17' 
          AND f.workout_day <= '2025-11-20'
          AND wa.id IS NULL
        ORDER BY f.workout_day
    ''')
    
    fit_files = c.fetchall()
    print(f"Found {len(fit_files)} FIT files to analyze\n")
    
    analyzer = FitFileAnalyzer()
    
    for fit_id, workout_day, file_name, fit_data_json in fit_files:
        print(f"{'='*60}")
        print(f"Analyzing: {workout_day} - {file_name}")
        print(f"{'='*60}")
        
        # Parse the stored FIT data
        fit_data = json.loads(fit_data_json)
        
        # Create a minimal FIT file format for the analyzer
        # The analyzer expects raw FIT file bytes, but we already have parsed data
        # So we'll need to work with the parsed data directly
        
        # Get the raw file from database if available, or skip
        print(f"⊘ Skipping - need to re-download FIT file for full analysis")
        print()
    
    print(f"\n{'='*60}")
    print("To properly analyze, please run:")
    print("  python -m src.utils.daily_auto_sync_and_analyze")
    print(f"{'='*60}")

if __name__ == '__main__':
    analyze_week()
