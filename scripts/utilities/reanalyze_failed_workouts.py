#!/usr/bin/env python3
"""
Reanalyze Failed Workouts Script

This script intelligently reanalyzes workouts that have:
- No AI analysis text
- Quota exceeded errors
- Other API failures

It prioritizes the current week first, then works backwards through history.
Stops automatically when it hits a new quota error to prevent waste.
Safe to run daily - will gradually fill in all gaps.

Usage:
    python reanalyze_failed_workouts.py
"""

import sys
from pathlib import Path
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.storage.database import WorkoutDatabase
from src.utils.fit_file_analyzer import FitFileAnalyzer
import json


def get_current_week_range():
    """Get the Monday-Sunday range for the current week"""
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).date()  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday
    return week_start, week_end


def needs_reanalysis(analysis_text: str) -> bool:
    """Check if a workout needs reanalysis based on its analysis text"""
    if not analysis_text:
        return True
    
    # Check for error indicators
    error_indicators = [
        'quota',
        '429',
        'rate limit',
        'all 7 models failed',
        'Could not generate analysis',
        'No analysis text available'
    ]
    
    analysis_lower = analysis_text.lower()
    return any(indicator.lower() in analysis_lower for indicator in error_indicators)


def is_quota_error(analysis_text: str) -> bool:
    """Check if an analysis text indicates a quota/rate limit error"""
    if not analysis_text:
        return False
    
    quota_indicators = ['quota', '429', 'rate limit']
    analysis_lower = analysis_text.lower()
    return any(indicator in analysis_lower for indicator in quota_indicators)


def main():
    print("🔄 Reanalyzing Failed Workouts")
    print("=" * 80)
    print()
    
    # Initialize
    db = WorkoutDatabase('data/fitness_data.db')
    analyzer = FitFileAnalyzer()
    
    # Get current week range
    week_start, week_end = get_current_week_range()
    print(f"📅 Current Week: {week_start} to {week_end}")
    print()
    
    # Get all workouts with analyses, ordered by date (newest first)
    # Prioritize current week, then work backwards
    query = '''
        SELECT 
            w.id as workout_id,
            w.workout_day,
            w.workout_title,
            wa.id as analysis_id,
            wa.analysis_text,
            wa.analysis_data,
            CASE 
                WHEN w.workout_day >= ? AND w.workout_day <= ? THEN 1
                ELSE 2
            END as priority
        FROM workouts w
        LEFT JOIN workout_analyses wa ON w.id = wa.workout_id
        WHERE wa.id IS NOT NULL  -- Only workouts that have been analyzed
        ORDER BY priority ASC, w.workout_day DESC
    '''
    
    import sqlite3
    conn = sqlite3.connect('data/fitness_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query, (week_start.strftime('%Y-%m-%d'), week_end.strftime('%Y-%m-%d')))
    rows = cursor.fetchall()
    conn.close()
    
    # Filter to workouts that need reanalysis
    workouts_to_fix = []
    for row in rows:
        if needs_reanalysis(row['analysis_text']):
            workouts_to_fix.append({
                'workout_id': row['workout_id'],
                'analysis_id': row['analysis_id'],
                'date': row['workout_day'],
                'title': row['workout_title'],
                'analysis_data': row['analysis_data'],
                'is_current_week': row['priority'] == 1
            })
    
    if not workouts_to_fix:
        print("✅ All workouts have successful AI analysis!")
        print("   Nothing to reanalyze.")
        return
    
    # Separate current week from historical
    current_week_workouts = [w for w in workouts_to_fix if w['is_current_week']]
    historical_workouts = [w for w in workouts_to_fix if not w['is_current_week']]
    
    print(f"📊 Found workouts needing reanalysis:")
    print(f"   • Current week: {len(current_week_workouts)}")
    print(f"   • Historical: {len(historical_workouts)}")
    print(f"   • Total: {len(workouts_to_fix)}")
    print()
    
    # Process workouts
    reanalyzed = 0
    skipped = 0
    quota_hit = False
    
    print("🚀 Starting reanalysis...")
    print("   (Will stop automatically if quota limit is hit)")
    print()
    
    for idx, workout in enumerate(workouts_to_fix, 1):
        if quota_hit:
            print(f"\n⏸️  Stopped: Hit quota limit. Run again tomorrow to continue.")
            print(f"   Completed: {reanalyzed}/{len(workouts_to_fix)}")
            break
        
        week_label = "📅 Current Week" if workout['is_current_week'] else "📚 Historical"
        print(f"[{idx}/{len(workouts_to_fix)}] {week_label}: {workout['date']} - {workout['title'][:50]}")
        
        try:
            # Parse analysis_data to get intervals and metrics
            analysis_data = workout['analysis_data']
            if isinstance(analysis_data, str):
                analysis_data = json.loads(analysis_data)
            
            # Get the parsed data with intervals
            parsed_data = analysis_data.get('parsed_data', {})
            intervals = analysis_data.get('intervals', {})
            peak_efforts = analysis_data.get('peak_efforts', {})
            
            # Generate new AI analysis using the private method
            print(f"   🤖 Generating AI analysis...")
            ai_analysis = analyzer._generate_ai_analysis(
                parsed_data=parsed_data,
                peak_efforts=peak_efforts,
                athlete_notes=None,
                intervals_data=intervals
            )
            
            # Check if we hit quota on this attempt
            if is_quota_error(ai_analysis):
                print(f"   ⚠️  Hit quota limit on this workout")
                quota_hit = True
                skipped += 1
                continue
            
            # Update the analysis in database
            db.update_workout_analysis_text(workout['analysis_id'], ai_analysis)
            
            reanalyzed += 1
            print(f"   ✅ Success! Analysis updated")
            
            # Rate limit: 10 seconds between API calls to avoid hitting quota
            if idx < len(workouts_to_fix):
                print(f"   ⏱️  Waiting 10 seconds...")
                time.sleep(10)
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
            skipped += 1
        
        print()
    
    # Summary
    print("=" * 80)
    print("📊 Summary:")
    print(f"   ✅ Successfully reanalyzed: {reanalyzed}")
    print(f"   ⏭️  Skipped/Failed: {skipped}")
    print(f"   📝 Remaining: {len(workouts_to_fix) - reanalyzed - skipped}")
    print()
    
    if quota_hit:
        print("💡 Tip: Run this script again tomorrow to continue filling gaps!")
    elif reanalyzed == len(workouts_to_fix):
        print("🎉 All workouts successfully reanalyzed!")
    
    print()


if __name__ == "__main__":
    main()
