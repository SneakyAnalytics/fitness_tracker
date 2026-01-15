#!/usr/bin/env python3
"""
Backfill workout analyses for all FIT files that have matching workouts.

This script:
1. Finds all FIT files that have been parsed but don't have workout analyses
2. Runs AI analysis on each one to generate interval data
3. This ensures historical workouts have accurate interval power for AI coaching

Usage:
    python backfill_workout_analyses.py [--days DAYS] [--dry-run]
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.fit_file_analyzer import FitFileAnalyzer
from src.storage.database import WorkoutDatabase


def main():
    parser = argparse.ArgumentParser(description='Backfill workout analyses for historical FIT files')
    parser.add_argument('--days', type=int, default=60, 
                       help='Number of days to look back (default: 60 for AI rolling window)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be analyzed without actually doing it')
    parser.add_argument('--force', action='store_true',
                       help='Re-analyze even if analysis already exists')
    args = parser.parse_args()

    print("=" * 80)
    print("🔄 BACKFILL WORKOUT ANALYSES")
    print("=" * 80)
    print(f"📅 Looking back: {args.days} days")
    print(f"🔍 Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"♻️  Force re-analyze: {args.force}")
    print()

    # Initialize
    db = WorkoutDatabase()
    analyzer = FitFileAnalyzer()

    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=args.days)

    print(f"📊 Querying FIT files from {start_date} to {end_date}")
    print()

    # Get all FIT files in date range that need analysis
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    c = conn.cursor()

    if args.force:
        # Get all FIT files in date range
        query = '''
            SELECT f.id, f.workout_day, f.workout_title, f.file_name, f.fit_data,
                   w.workout_data
            FROM fit_files f
            LEFT JOIN workouts w ON f.workout_day = w.workout_day 
                AND f.workout_title = w.workout_title
                AND f.sequence_number = w.sequence_number
            WHERE f.workout_day >= ? AND f.workout_day <= ?
                AND json_extract(f.fit_data, '$.sport') = 'cycling'
            ORDER BY 
                -- Prioritize entries with valid TSS (> 1)
                CASE WHEN CAST(json_extract(f.fit_data, '$.power_metrics.tss') AS REAL) > 1 THEN 0 ELSE 1 END,
                f.workout_day DESC
        '''
    else:
        # Get FIT files without analysis
        query = '''
            SELECT f.id, f.workout_day, f.workout_title, f.file_name, f.fit_data,
                   w.workout_data
            FROM fit_files f
            LEFT JOIN workouts w ON f.workout_day = w.workout_day 
                AND f.workout_title = w.workout_title
                AND f.sequence_number = w.sequence_number
            LEFT JOIN workout_analyses wa ON f.id = wa.fit_file_id
            WHERE f.workout_day >= ? AND f.workout_day <= ?
                AND wa.id IS NULL
                AND json_extract(f.fit_data, '$.sport') = 'cycling'
            ORDER BY 
                -- Prioritize entries with valid TSS (> 1)
                CASE WHEN CAST(json_extract(f.fit_data, '$.power_metrics.tss') AS REAL) > 1 THEN 0 ELSE 1 END,
                f.workout_day DESC
        '''

    c.execute(query, (str(start_date), str(end_date)))
    fit_files = c.fetchall()
    conn.close()

    print(f"📁 Found {len(fit_files)} FIT files to {'re-analyze' if args.force else 'analyze'}")
    print()

    if len(fit_files) == 0:
        print("✅ No FIT files need analysis!")
        return

    # Group by workout type for reporting
    import json
    by_type = {}
    for row in fit_files:
        workout_data_json = row[5]
        if workout_data_json:
            try:
                workout_data = json.loads(workout_data_json)
                workout_type = workout_data.get('type', 'Unknown')
            except:
                workout_type = 'Unknown'
        else:
            workout_type = 'Unknown'
        by_type[workout_type] = by_type.get(workout_type, 0) + 1

    print("📋 Breakdown by workout type:")
    for wtype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"   {wtype}: {count} workouts")
    print()

    if args.dry_run:
        print("🏁 Dry run complete - no analyses performed")
        return

    # Process each FIT file
    print("🚀 Starting analysis...")
    print("-" * 80)

    analyzed = 0
    skipped = 0
    errors = 0
    bike_count = 0
    processed_dates = set()  # Track dates we've successfully analyzed

    for row in fit_files:
        fit_id, workout_day, workout_title, file_name, fit_data, workout_data_json = row

        # Skip if we've already successfully analyzed this date (deduplication)
        if workout_day in processed_dates:
            print(f"\n⏭️  {workout_day} - Already analyzed (duplicate entry)")
            skipped += 1
            continue

        # Parse workout type
        workout_type = 'Unknown'
        if workout_data_json:
            try:
                import json
                workout_data = json.loads(workout_data_json)
                workout_type = workout_data.get('type', 'Unknown')
            except:
                pass

        try:
            # Show progress
            title_short = workout_title[:70] if workout_title else file_name
            print(f"\n📊 {workout_day} - {title_short}")
            print(f"   Type: {workout_type or 'Unknown'} | FIT ID: {fit_id}")

            if not fit_data:
                print(f"   ⏭️  No FIT data stored")
                skipped += 1
                continue

            # Track bike workouts for interval power
            if workout_type == 'Bike':
                bike_count += 1

            # If force mode, delete existing analysis
            if args.force:
                import sqlite3
                force_conn = sqlite3.connect(db.db_path)
                force_c = force_conn.cursor()
                force_c.execute('DELETE FROM workout_analyses WHERE fit_file_id = ?', (fit_id,))
                force_conn.commit()
                force_conn.close()
                print(f"   🔄 Force mode: Deleted existing analysis")

            # Parse the JSON FIT data
            try:
                import json
                parsed_data = json.loads(fit_data)
            except Exception as e:
                print(f"   ❌ Error parsing JSON FIT data: {str(e)}")
                skipped += 1
                continue
            
            # Analyze using parsed data directly (since database stores JSON, not raw FIT bytes)
            result = analyzer.analyze_workout_from_parsed_data(
                parsed_data,
                athlete_ftp=305  # TODO: Get from athlete settings
            )

            if result:
                # Check if AI analysis failed due to quota/API issues
                ai_text = result.get('ai_analysis', '')
                if 'all' in ai_text.lower() and 'models failed' in ai_text.lower():
                    print(f"   ❌ API quota exhausted - stopping backfill")
                    print(f"   💡 Run this script again tomorrow to continue")
                    errors += 1
                    break  # Stop processing - don't waste API calls
                
                # Check for quota-related errors
                if 'quota exceeded' in ai_text.lower() or 'resource exhausted' in ai_text.lower():
                    print(f"   ❌ API quota limit hit - stopping backfill")
                    print(f"   💡 Free tier limit reached. Resume tomorrow or upgrade API plan")
                    errors += 1
                    break
                
                # Count intervals detected
                intervals_data = result.get('intervals', {})
                summary = intervals_data.get('summary', {}) if intervals_data else {}
                intervals_detected = summary.get('total_intervals', 0)
                
                # Save analysis to database
                analysis_id = db.store_workout_analysis(
                    fit_file_id=fit_id,
                    analysis_text=result.get('ai_analysis', ''),
                    analysis_data=result,  # Full data including intervals
                    peak_efforts=result.get('peak_efforts'),
                    model_used='gemini-2.0-flash-exp'
                )
                
                print(f"   ✅ Analysis saved (ID: {analysis_id}) - {intervals_detected} intervals detected")
                analyzed += 1
                
                # Mark this date as successfully processed (deduplication)
                processed_dates.add(workout_day)

                # Special note for bike workouts with intervals
                if workout_type == 'Bike' and intervals_detected > 0:
                    # Check if it's an interval-based workout
                    by_type = summary.get('by_type', {})
                    
                    if 'vo2max' in by_type or 'threshold' in by_type or 'work' in by_type:
                        print(f"   🎯 Interval workout - AI coach will now see accurate power!")
            else:
                print(f"   ⏭️  Skipped (already analyzed or no workout match)")
                skipped += 1

            # Rate limit: 6 seconds between API calls to avoid quota issues
            time.sleep(6)

        except Exception as e:
            errors += 1
            print(f"   ❌ Error: {str(e)[:100]}")
            # Continue with next file even if one fails

    print()
    print("=" * 80)
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"✅ Analyzed: {analyzed}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Errors: {errors}")
    print(f"🚴 Bike workouts analyzed: {bike_count}")
    
    if errors > 0 and analyzed > 0:
        print()
        print("⚠️  Script stopped early due to API quota limit")
        print(f"   Progress: {analyzed}/{len(fit_files)} files analyzed")
        print(f"   Remaining: {len(fit_files) - analyzed - skipped} files")
        print(f"   💡 Run again tomorrow to continue from where you left off")
    elif analyzed > 0:
        print()
        print("✅ All analyses completed successfully!")
        print("   AI coach now has interval data for historical workouts")
    
    print()
    print("💡 Tip: Run this script weekly to keep analyses up to date")
    print("💡 Use --days 90 for a longer historical analysis window")
    print("💡 Free Gemini API tier: ~15 requests/minute, 1500 requests/day")


if __name__ == '__main__':
    main()
