#!/usr/bin/env python3
"""
Regenerate Zwift workout files for Week 53 with new dynamic alert system.

Run this AFTER regenerating Week 53 via the Streamlit UI.
"""

import sqlite3
import os
from src.storage.database import WorkoutDatabase
from src.utils.zwift_workout_generator import generate_zwift_workouts_from_db

def main():
    # Create database connection object
    db = WorkoutDatabase('data/fitness_data.db')
    
    # Get Week 53 info
    conn = sqlite3.connect('data/fitness_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT weekNumber, startDate FROM weekly_plans WHERE weekNumber = 53")
    week_info = cursor.fetchone()
    conn.close()
    
    if not week_info:
        print("❌ Week 53 not found in database")
        print("📝 Please regenerate Week 53 via the Streamlit UI first:")
        print("   1. Go to 'Generate AI Workout Plan' section")
        print("   2. Select week starting Nov 17, 2025")
        print("   3. Use Haiku 4.5 for analysis, Sonnet 4.5 for generation")
        print("   4. Then run this script again")
        return
    
    week_num, start_date = week_info
    print(f"✅ Found Week {week_num} starting {start_date}")
    print()
    
    # Expand the Zwift directory path properly
    zwift_dir = os.path.expanduser("~/Documents/Zwift/Workouts/6870291")
    
    # Generate Zwift files with new dynamic content
    print("🚴 Regenerating Zwift files with new dynamic alerts...")
    print("   ✨ 10-15 messages per workout")
    print("   ✨ Zero repetition API-based content")
    print("   ✨ Trivia questions split from answers (60s thinking time)")
    print("   ✨ Mix of quotes, jokes, facts, and trivia")
    print()
    
    try:
        zwift_files = generate_zwift_workouts_from_db(
            db_connection=db,
            start_date=start_date,
            end_date="2025-11-23",
            output_dir=zwift_dir,
            week_number=week_num
        )
        
        print()
        print(f"✅ Generated {len(zwift_files)} Zwift workout files!")
        print()
        print("📄 Files created:")
        for file in zwift_files:
            print(f"   • {os.path.basename(file)}")
        print()
        print(f"📁 Location: {zwift_dir}/Week_{week_num}/")
        print()
        print("🎯 Ready for Zwift! The old files have been replaced with new dynamic alerts.")
        
    except Exception as e:
        print(f"❌ Error generating Zwift files: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
