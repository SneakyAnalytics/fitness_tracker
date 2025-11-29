#!/usr/bin/env python3
"""
Analyze FIT files from cached downloads with smart workout matching
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
    
    # FIT files to analyze from Downloads
    fit_files = [
        ("~/Downloads/trainingpeaks_extracted/WorkoutFileExport-Robinson-Jake-2025-11-17-2025-11-17/zwift-activity-2009248879257600000.fit", 623),
        ("~/Downloads/trainingpeaks_extracted/WorkoutFileExport-Robinson-Jake-2025-11-18-2025-11-18/zwift-activity-2009997700933648416.fit", 624),
        ("~/Downloads/trainingpeaks_extracted/WorkoutFileExport-Robinson-Jake-2025-11-18-2025-11-18/zwift-activity-2010005754467090448.fit", 625),
        ("~/Downloads/trainingpeaks_extracted/WorkoutFileExport-Robinson-Jake-2025-11-19-2025-11-19/zwift-activity-2010366798410579968.fit", 626),
        ("~/Downloads/trainingpeaks_extracted/WorkoutFileExport-Robinson-Jake-2025-11-20-2025-11-20/zwift-activity-2011067968607240208.fit", 627),
    ]
    
    print(f"\n🎯 Analyzing {len(fit_files)} FIT files with smart matching...\n")
    
    # Get athlete FTP
    settings = db.get_athlete_settings()
    ftp_watts = settings.get('ftp', 300)
    print(f"Using FTP: {ftp_watts}W\n")
    
    for idx, (fit_path, fit_id) in enumerate(fit_files, 1):
        fit_path_expanded = Path(fit_path).expanduser()
        
        if not fit_path_expanded.exists():
            print(f"[{idx}/{len(fit_files)}] ⚠️  File not found: {fit_path}")
            continue
        
        print(f"[{idx}/{len(fit_files)}] {fit_path_expanded.name}")
        print(f"   FIT file ID: {fit_id}")
        
        try:
            # Read FIT file
            with open(fit_path_expanded, 'rb') as f:
                fit_bytes = f.read()
            
            # Analyze the workout (uses smart matching)
            result = analyzer.analyze_workout(
                fit_file_content=fit_bytes,
                athlete_ftp=ftp_watts,
                athlete_notes=None
            )
            
            if result and result.get('ai_analysis') and 'skipped' not in result['ai_analysis'].lower():
                # Store the analysis
                analysis_id = db.store_workout_analysis(
                    fit_file_id=fit_id,
                    analysis_text=result['ai_analysis'],
                    peak_efforts=result.get('peak_efforts', {})
                )
                print(f"   ✅ Analysis complete - ID: {analysis_id}\n")
            else:
                skip_reason = result.get('ai_analysis', 'Unknown') if result else 'No result'
                print(f"   ⚠️  Analysis skipped: {skip_reason}\n")
                
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("\n✅ Batch analysis complete!")
    
    # Show summary
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM workout_analyses WHERE fit_file_id IN (623, 624, 625, 626, 627)')
    count = c.fetchone()[0]
    conn.close()
    print(f"Total analyses for Nov 17-20: {count}/5")

if __name__ == "__main__":
    main()
