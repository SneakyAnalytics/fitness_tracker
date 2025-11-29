#!/usr/bin/env python3
"""
Quick test script to fetch Mon-Wed workouts and verify historical visualization works.
"""

from datetime import date
from src.utils.daily_auto_sync_and_analyze import DailyAutoSyncAndAnalyze

def main():
    print("=" * 70)
    print("Testing Historical Visualization with Mon-Wed Workouts")
    print("=" * 70)
    print()
    
    automation = DailyAutoSyncAndAnalyze(db_path='data/fitness_data.db')
    
    # Dates to process
    dates = [
        date(2025, 11, 17),  # Monday
        date(2025, 11, 18),  # Tuesday
        date(2025, 11, 19),  # Wednesday
    ]
    
    for target_date in dates:
        print(f"\n{'='*70}")
        print(f"Processing {target_date.strftime('%A, %B %d, %Y')}")
        print(f"{'='*70}\n")
        
        results = automation.run_daily_automation(
            target_date=target_date,
            ftp_watts=330,
            cleanup=True
        )
        
        # Summary
        print(f"\n📊 Results for {target_date}:")
        print(f"   Files Downloaded: {results['fit_files_downloaded']}")
        print(f"   Workouts Analyzed: {results['workouts_analyzed']}")
        print(f"   Personal Bests: {results['personal_bests']}")
        if results['errors']:
            print(f"   Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"     - {error}")
    
    print("\n" + "=" * 70)
    print("✅ Complete! Now check the Historical Data tab in Streamlit")
    print("=" * 70)
    print("\nRun: streamlit run src/ui/streamlit_app.py")
    print()

if __name__ == "__main__":
    main()
