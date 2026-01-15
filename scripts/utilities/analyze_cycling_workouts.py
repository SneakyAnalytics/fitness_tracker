#!/usr/bin/env python3
"""
Analyze all cycling workouts from the past 3 weeks
Ensures interval data is properly stored for accurate AI coaching
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from storage.database import WorkoutDatabase
from utils.fit_file_analyzer import FitFileAnalyzer

def get_cycling_workouts_needing_analysis(days_back=21):
    """Get all cycling workouts from the past N days that need analysis"""
    import sqlite3
    
    conn = sqlite3.connect('data/fitness_data.db')
    c = conn.cursor()
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    
    print(f"Finding cycling workouts from {start_date} to {end_date}...")
    
    # Find all cycling workouts with FIT files but missing or incomplete analysis_data
    c.execute('''
        SELECT 
            w.id,
            w.workout_day,
            w.workout_title,
            f.id as fit_file_id,
            f.fit_data,
            wa.id as analysis_id,
            wa.analysis_data
        FROM workouts w
        JOIN fit_files f ON w.fit_file_id = f.id
        LEFT JOIN workout_analyses wa ON w.id = wa.workout_id
        WHERE w.workout_day BETWEEN ? AND ?
          AND json_extract(w.workout_data, '$.type') = 'Bike'
        ORDER BY w.workout_day
    ''', (str(start_date), str(end_date)))
    
    workouts = []
    for row in c.fetchall():
        workout_id, workout_day, workout_title, fit_file_id, fit_data_json, analysis_id, analysis_data_json = row
        
        # Check if analysis_data exists and has intervals
        needs_analysis = True
        if analysis_data_json:
            try:
                analysis_data = json.loads(analysis_data_json)
                if analysis_data.get('intervals'):
                    needs_analysis = False  # Already has interval data
            except:
                pass
        
        if needs_analysis:
            workouts.append({
                'workout_id': workout_id,
                'workout_day': workout_day,
                'workout_title': workout_title,
                'fit_file_id': fit_file_id,
                'fit_data': fit_data_json,
                'has_analysis': analysis_id is not None
            })
    
    conn.close()
    return workouts

def analyze_workout(workout, db, analyzer, ftp):
    """Analyze a single workout and store results"""
    workout_id = workout['workout_id']
    workout_day = workout['workout_day']
    workout_title = workout['workout_title']
    fit_file_id = workout['fit_file_id']
    
    print(f"\n{'='*80}")
    print(f"📅 {workout_day}: {workout_title[:60]}")
    print(f"   Workout ID: {workout_id}, FIT file ID: {fit_file_id}")
    
    try:
        # Parse FIT data
        fit_data = json.loads(workout['fit_data'])
        
        # Detect intervals
        print(f"   🔍 Detecting intervals with FTP={ftp}W...")
        intervals_data = analyzer._detect_intervals(fit_data, athlete_ftp=float(ftp))
        
        if not intervals_data or not intervals_data.get('intervals'):
            print(f"   ⊘ No intervals detected (likely recovery/endurance ride)")
            
            # Still store analysis with empty intervals
            analysis_result = {
                'parsed_data': fit_data,
                'intervals': {},
                'ai_analysis': f"Recovery/endurance workout - No structured intervals",
                'analyzed_at': workout_day
            }
        else:
            print(f"   ✓ Found {intervals_data.get('interval_count', 0)} intervals")
            print(f"   📝 {intervals_data.get('description', 'N/A')}")
            
            # Extract work interval power for high-intensity workouts
            intervals_list = intervals_data.get('intervals', [])
            work_intervals = [i for i in intervals_list if i.get('type') in ['vo2max', 'threshold', 'tempo', 'sweetspot', 'work']]
            
            if work_intervals:
                total_power = sum(i.get('avg_power', 0) for i in work_intervals)
                avg_interval_power = total_power / len(work_intervals)
                print(f"   🔥 Average work interval power: {avg_interval_power:.1f}W")
                
                # Show breakdown
                for i, interval in enumerate(work_intervals[:5]):  # Show first 5
                    avg_power = interval.get('avg_power', 0)
                    duration = interval.get('duration_sec', 0)
                    itype = interval.get('type', 'work')
                    intensity = interval.get('intensity_zone', 'N/A')
                    print(f"      - Interval {i+1}: {avg_power:.0f}W for {duration}s ({itype}, {intensity})")
                
                analysis_text = f"Interval workout - {intervals_data.get('description')} - Avg work interval power: {avg_interval_power:.1f}W"
            else:
                analysis_text = f"Structured workout - {intervals_data.get('description')}"
            
            analysis_result = {
                'parsed_data': fit_data,
                'intervals': intervals_data,
                'ai_analysis': analysis_text,
                'analyzed_at': workout_day
            }
        
        # Store or update analysis
        if workout['has_analysis']:
            # Update existing analysis
            import sqlite3
            conn = sqlite3.connect('data/fitness_data.db')
            c = conn.cursor()
            c.execute('''
                UPDATE workout_analyses 
                SET analysis_data = ?,
                    analysis_text = ?,
                    model_used = 'interval_detector'
                WHERE workout_id = ?
            ''', (json.dumps(analysis_result), analysis_result['ai_analysis'], workout_id))
            conn.commit()
            conn.close()
            print(f"   ✅ Updated existing analysis")
        else:
            # Create new analysis
            analysis_id = db.store_workout_analysis(
                workout_id=workout_id,
                fit_file_id=fit_file_id,
                analysis_text=analysis_result['ai_analysis'],
                model_used='interval_detector',
                analysis_data=analysis_result,
                peak_efforts={}
            )
            print(f"   ✅ Created new analysis (ID: {analysis_id})")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚴 Analyzing Cycling Workouts for Past 3 Weeks")
    print("=" * 80)
    
    # Get workouts needing analysis
    workouts = get_cycling_workouts_needing_analysis(days_back=21)
    
    if not workouts:
        print("\n✅ All cycling workouts already have interval analysis!")
        return
    
    print(f"\n📊 Found {len(workouts)} cycling workouts needing interval analysis")
    
    # Get FTP from athlete settings
    db = WorkoutDatabase('data/fitness_data.db')
    settings = db.get_athlete_settings()
    ftp = settings.get('ftp', 315)
    print(f"Using athlete FTP: {ftp}W")
    
    # Create analyzer (no AI needed for interval detection)
    analyzer = FitFileAnalyzer(use_dynamic_models=False)
    
    # Analyze each workout
    success_count = 0
    for workout in workouts:
        if analyze_workout(workout, db, analyzer, ftp):
            success_count += 1
    
    print(f"\n{'='*80}")
    print(f"✅ Successfully analyzed {success_count}/{len(workouts)} workouts")
    print(f"\n💡 Interval data is now available for accurate AI coaching analysis")
    print(f"   The weekly AI analysis will now use actual work interval power")
    print(f"   instead of whole-workout averages.")

if __name__ == '__main__':
    main()
