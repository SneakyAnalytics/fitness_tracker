#!/usr/bin/env python3
"""
Analyze specific FIT files from the database (Nov 17-20)
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.fit_file_analyzer import FitFileAnalyzer
from src.storage.database import WorkoutDatabase

def main():
    db_path = Path(__file__).parent / 'data' / 'fitness_data.db'
    db = WorkoutDatabase(str(db_path))
    analyzer = FitFileAnalyzer(str(db_path))
    
    # Get FIT files for Nov 17-20
    import sqlite3
    import json
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    c.execute('''
        SELECT id, workout_day, file_name, fit_data
        FROM fit_files
        WHERE workout_day >= '2025-11-17' AND workout_day <= '2025-11-20'
        ORDER BY workout_day
    ''')
    
    files = c.fetchall()
    conn.close()
    
    print(f"\n🎯 Analyzing {len(files)} FIT files from Nov 17-20...\n")
    
    for idx, (fit_id, workout_day, file_name, file_data) in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] {workout_day}: {file_name}")
        print(f"   FIT file ID: {fit_id}")
        
        if not file_data:
            print(f"   ⚠️  No file data stored in database\n")
            continue
        
        # Get athlete settings for FTP
        settings = db.get_athlete_settings()
        ftp_watts = settings.get('ftp', 300)
        print(f"   FTP: {ftp_watts}W")
        
        try:
            # Analyze the workout
            result = analyzer.analyze_workout(
                fit_file_content=file_data,
                athlete_ftp=ftp_watts,
                athlete_notes=None
            )
            
            if result and result.get('ai_analysis'):
                # Store the analysis
                analysis_id = db.store_workout_analysis(
                    fit_file_id=fit_id,
                    analysis_text=result['ai_analysis'],
                    peak_efforts=result.get('peak_efforts', {})
                )
                print(f"   ✅ Analysis complete - ID: {analysis_id}\n")
            else:
                print(f"   ⚠️  Analysis skipped (no proposed workout or non-cycling)\n")
                
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("\n✅ Batch analysis complete!")

if __name__ == "__main__":
    main()
