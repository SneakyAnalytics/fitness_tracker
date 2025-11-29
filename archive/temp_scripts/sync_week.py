#!/usr/bin/env python3
"""
Download and analyze workouts day-by-day for Nov 17-20, 2025
"""
import os
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from src.utils.daily_auto_sync_and_analyze import DailyAutoSyncAndAnalyze

load_dotenv()

def download_and_analyze_day(target_date: date):
    """Download and analyze workouts for a specific day"""
    print(f"\n{'='*60}")
    print(f"Processing {target_date.strftime('%A, %B %d, %Y')}")
    print(f"{'='*60}")
    
    sync = DailyAutoSyncAndAnalyze()
    results = sync.run_daily_automation(target_date=target_date)
    
    print(f"\nResults:")
    print(f"  FIT files downloaded: {results.get('fit_files_downloaded', 0)}")
    print(f"  Workouts analyzed: {results.get('workouts_analyzed', 0)}")
    print(f"  Personal bests: {results.get('personal_bests_found', 0)}")
    
    return results

if __name__ == '__main__':
    # Process each day from Nov 17-20
    start_date = date(2025, 11, 17)  # Monday
    end_date = date(2025, 11, 20)    # Thursday
    
    current_date = start_date
    total_workouts = 0
    total_pbs = 0
    
    while current_date <= end_date:
        results = download_and_analyze_day(current_date)
        total_workouts += results.get('workouts_analyzed', 0)
        total_pbs += results.get('personal_bests_found', 0)
        current_date += timedelta(days=1)
    
    print(f"\n{'='*60}")
    print(f"✅ WEEK SYNC COMPLETE!")
    print(f"{'='*60}")
    print(f"Total workouts analyzed: {total_workouts}")
    print(f"Total personal bests: {total_pbs}")
    print(f"{'='*60}")
