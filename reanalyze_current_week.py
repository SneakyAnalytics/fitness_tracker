#!/usr/bin/env python3
"""
Quick utility to delete and re-analyze current week's workouts (Nov 17-20, 2025)
This will demonstrate the new enhanced AI analysis with:
- Time-series trend analysis (power fade, HR drift, cadence)
- Detailed proposed workout adherence scoring
- Interval-by-interval execution analysis
"""

import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.trainingpeaks_sync import TrainingPeaksSync


def delete_workout_data(start_date: str, end_date: str):
    """Delete all workout data for the specified date range"""
    print(f"\n{'='*80}")
    print(f"STEP 1: Cleaning up existing data for {start_date} to {end_date}")
    print(f"{'='*80}\n")
    
    db_path = 'data/fitness_data.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Delete workout analyses first (foreign key constraint)
        print("🗑️  Deleting workout analyses...")
        c.execute('''
            DELETE FROM workout_analyses 
            WHERE fit_file_id IN (
                SELECT id FROM fit_files 
                WHERE workout_day >= ? AND workout_day <= ?
            )
        ''', (start_date, end_date))
        analyses_deleted = c.rowcount
        print(f"   ✓ Deleted {analyses_deleted} analyses")
        
        # Delete FIT files
        print("🗑️  Deleting FIT files...")
        c.execute('''
            DELETE FROM fit_files 
            WHERE workout_day >= ? AND workout_day <= ?
        ''', (start_date, end_date))
        files_deleted = c.rowcount
        print(f"   ✓ Deleted {files_deleted} FIT files")
        
        # Delete CSV workout data
        print("🗑️  Deleting CSV workout data...")
        c.execute('''
            DELETE FROM workouts 
            WHERE workout_day >= ? AND workout_day <= ?
        ''', (start_date, end_date))
        workouts_deleted = c.rowcount
        print(f"   ✓ Deleted {workouts_deleted} CSV workout records")
        
        # Delete daily metrics
        print("🗑️  Deleting daily metrics...")
        c.execute('''
            DELETE FROM daily_metrics 
            WHERE date >= ? AND date <= ?
        ''', (start_date, end_date))
        metrics_deleted = c.rowcount
        print(f"   ✓ Deleted {metrics_deleted} daily metric records")
        
        conn.commit()
        print(f"\n✅ Cleanup complete!")
        print(f"   Total items deleted: {analyses_deleted + files_deleted + workouts_deleted + metrics_deleted}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def reupload_workout_data(start_date: str, end_date: str):
    """Re-upload workout data using TrainingPeaks sync"""
    print(f"\n{'='*80}")
    print(f"STEP 2: Re-uploading data for {start_date} to {end_date}")
    print(f"{'='*80}\n")
    
    try:
        # Initialize TrainingPeaks sync
        tp_sync = TrainingPeaksSync()
        
        # Convert date strings to date objects
        from datetime import datetime
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Run sync for the date range
        print(f"🔄 Syncing TrainingPeaks data...")
        results = tp_sync.run_sync(start_date=start_dt, end_date=end_dt)
        
        if results:
            print(f"\n✅ Re-upload complete!")
            print(f"   FIT files uploaded: {results.get('fit_files', 0)}")
            print(f"   Workouts CSV: {'✅' if results.get('workouts') else '❌'}")
            print(f"   Metrics CSV: {'✅' if results.get('metrics') else '❌'}")
            
            # Show which FIT files were uploaded
            if results.get('fit_file_paths'):
                print(f"\n📁 Uploaded FIT files:")
                for path in results['fit_file_paths']:
                    print(f"   • {Path(path).name}")
            
            return True
        else:
            print(f"\n⚠️  Sync completed but no results returned")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during re-upload: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_new_analysis():
    """Verify that new analyses have the enhanced features"""
    print(f"\n{'='*80}")
    print(f"STEP 3: Verifying new analysis features")
    print(f"{'='*80}\n")
    
    db_path = 'data/fitness_data.db'
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Get latest workout analysis
        c.execute('''
            SELECT wa.analysis_text, ff.file_name, ff.workout_day
            FROM workout_analyses wa
            JOIN fit_files ff ON wa.fit_file_id = ff.id
            WHERE ff.workout_day >= '2025-11-17'
            ORDER BY ff.workout_day DESC
            LIMIT 1
        ''')
        
        row = c.fetchone()
        
        if row:
            analysis_text = row[0]
            file_name = row[1]
            workout_day = row[2]
            
            print(f"📊 Latest Analysis: {file_name} ({workout_day})")
            print(f"\n{'─'*80}\n")
            
            # Check for new features in the analysis
            features_found = []
            
            if "ADHERENCE SCORE" in analysis_text or "EXECUTION QUALITY" in analysis_text:
                features_found.append("✓ Adherence scoring")
            
            if "POWER PROGRESSION" in analysis_text or "power progression" in analysis_text.lower():
                features_found.append("✓ Power progression analysis")
            
            if "HR drift" in analysis_text or "HR DRIFT" in analysis_text:
                features_found.append("✓ HR drift analysis")
            
            if "cadence" in analysis_text.lower():
                features_found.append("✓ Cadence analysis")
            
            if "INTERVAL" in analysis_text.upper() or "interval" in analysis_text.lower():
                features_found.append("✓ Interval-specific analysis")
            
            if features_found:
                print("🎉 New analysis features detected:")
                for feature in features_found:
                    print(f"   {feature}")
            else:
                print("⚠️  Could not detect new analysis features")
            
            # Show preview of analysis
            print(f"\n{'─'*80}")
            print("📝 Analysis Preview (first 500 chars):")
            print(f"{'─'*80}\n")
            print(analysis_text[:500] + "..." if len(analysis_text) > 500 else analysis_text)
            print(f"\n{'─'*80}")
            
            return True
        else:
            print("⚠️  No workout analyses found for Nov 17-20")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying analysis: {e}")
        return False
    finally:
        conn.close()


def main():
    """Main execution flow"""
    print(f"\n{'█'*80}")
    print(f"{'█'*80}")
    print(f"  RE-ANALYZE CURRENT WEEK WITH ENHANCED AI ANALYSIS")
    print(f"  Date Range: November 17-20, 2025")
    print(f"{'█'*80}")
    print(f"{'█'*80}\n")
    
    # Date range
    start_date = "2025-11-17"
    end_date = "2025-11-20"
    
    # Step 1: Delete existing data
    if not delete_workout_data(start_date, end_date):
        print("\n❌ Failed to clean up data. Aborting.")
        return 1
    
    print("\n⏸️  Pausing 2 seconds before re-upload...")
    time.sleep(2)
    
    # Step 2: Re-upload data
    if not reupload_workout_data(start_date, end_date):
        print("\n❌ Failed to re-upload data. Check logs above.")
        return 1
    
    print("\n⏸️  Pausing 3 seconds before verification...")
    time.sleep(3)
    
    # Step 3: Verify new analysis
    verify_new_analysis()
    
    print(f"\n{'█'*80}")
    print(f"  ✅ PROCESS COMPLETE!")
    print(f"  Check your Streamlit app to see the enhanced analysis")
    print(f"{'█'*80}\n")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
