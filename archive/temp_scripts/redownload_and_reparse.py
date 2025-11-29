#!/usr/bin/env python3
"""
Re-download FIT files from TrainingPeaks and re-parse them with updated parser.
This will fix HR zone calculations and add time series data for visualization.
"""
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.utils.trainingpeaks_sync import TrainingPeaksSync
from src.utils.fit_file_analyzer import FitFileAnalyzer
from src.storage.database import WorkoutDatabase

load_dotenv()

DB_PATH = Path(__file__).parent / 'data' / 'fitness_data.db'

def redownload_and_analyze(start_date: str, end_date: str):
    """
    Re-download FIT files from TrainingPeaks and re-analyze them
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    from datetime import datetime as dt
    
    # Convert string dates to date objects
    start_dt = dt.strptime(start_date, '%Y-%m-%d').date()
    end_dt = dt.strptime(end_date, '%Y-%m-%d').date()
    
    db = WorkoutDatabase()
    analyzer = FitFileAnalyzer()
    
    # Initialize TrainingPeaks sync
    tp_sync = TrainingPeaksSync()
    
    # Download FIT files for date range
    print(f"\nDownloading FIT files from {start_date} to {end_date}...")
    results = tp_sync.run_sync(start_date=start_dt, end_date=end_dt)
    
    if not results or results.get('fit_files') == 0:
        print("No FIT files downloaded")
        return
    
    print(f"\nDownloaded {results.get('fit_files', 0)} FIT files")
    
    # Find the downloaded files in temp directory
    temp_dir = Path(__file__).parent / 'data' / 'temp'
    fit_files = list(temp_dir.glob('*.fit'))
    
    if not fit_files:
        print("No FIT files found in temp directory")
        return
    
    # Process each file
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        for fit_path in fit_files:
            print(f"\nProcessing {fit_path.name}...")
            
            # Read and analyze
            with open(fit_path, 'rb') as f:
                fit_content = f.read()
            
            analysis_result = analyzer.analyze_workout(fit_content)
            
            if not analysis_result:
                print(f"  ✗ Analysis failed")
                continue
            
            # Extract workout date from parsed data
            parsed_data = analysis_result.get('parsed_data', {})
            workout_date = parsed_data.get('start_time', '')[:10] if parsed_data.get('start_time') else None
            
            if not workout_date:
                print(f"  ✗ Could not determine workout date")
                continue
            
            # Store in fit_files table with updated parsed data
            import json
            import base64
            
            c.execute('''
                INSERT OR REPLACE INTO fit_files 
                (workout_day, workout_title, fit_data, file_name)
                VALUES (?, ?, ?, ?)
            ''', (
                workout_date,
                fit_path.stem,
                json.dumps(parsed_data),  # Store new parsed data with time series
                fit_path.name
            ))
            
            fit_file_id = c.lastrowid
            
            # Update or create workout analysis
            c.execute('SELECT id FROM workout_analyses WHERE fit_file_id = ?', (fit_file_id,))
            existing = c.fetchone()
            
            if existing:
                analysis_id = existing[0]
                c.execute('''
                    UPDATE workout_analyses
                    SET analysis_text = ?,
                        analysis_data = ?,
                        peak_efforts = ?,
                        analyzed_at = ?,
                        model_used = ?
                    WHERE id = ?
                ''', (
                    analysis_result.get('ai_analysis', ''),
                    str(parsed_data),
                    str(analysis_result.get('peak_efforts', {})),
                    datetime.now().isoformat(),
                    'gemini-2.0-flash',
                    analysis_id
                ))
                print(f"  ✓ Updated analysis ID {analysis_id} for {workout_date}")
            else:
                c.execute('''
                    INSERT INTO workout_analyses 
                    (fit_file_id, analysis_text, analysis_data, peak_efforts, analyzed_at, model_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    fit_file_id,
                    analysis_result.get('ai_analysis', ''),
                    str(parsed_data),
                    str(analysis_result.get('peak_efforts', {})),
                    datetime.now().isoformat(),
                    'gemini-2.0-flash'
                ))
                print(f"  ✓ Created analysis ID {c.lastrowid} for {workout_date}")
            
            # Show HR zone improvement
            hr_metrics = parsed_data.get('hr_metrics', {})
            if hr_metrics:
                print(f"    Avg HR: {hr_metrics.get('average_hr', 0):.0f} bpm")
                zones = hr_metrics.get('zones', {})
                if zones:
                    print(f"    Zones: Z1={zones.get('Zone 1 (Recovery)', 0):.0f}% Z2={zones.get('Zone 2 (Endurance)', 0):.0f}% Z3={zones.get('Zone 3 (Tempo)', 0):.0f}%")
            
            # Show time series availability
            time_series = parsed_data.get('time_series', {})
            if time_series:
                power_count = len([x for x in time_series.get('power', []) if x])
                hr_count = len([x for x in time_series.get('hr', []) if x])
                cadence_count = len([x for x in time_series.get('cadence', []) if x])
                print(f"    Time series: {power_count} power, {hr_count} HR, {cadence_count} cadence samples")
        
        conn.commit()
        print("\n✓ Re-download and re-analysis complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        conn.close()
        # Cleanup downloaded files
        for fit_path in fit_files:
            if fit_path.exists():
                fit_path.unlink()

if __name__ == '__main__':
    # Re-download and analyze Nov 18-19 workouts
    redownload_and_analyze('2025-11-18', '2025-11-19')
