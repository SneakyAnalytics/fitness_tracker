#\!/usr/bin/env python3

import sqlite3
import os

def reset_planning_tables():
    """Reset the daily_plans, proposed_workouts, and workout_performance tables"""
    db_path = "data/fitness_data.db"
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # First back up the tables to be safe
        print("Creating backup tables...")
        c.execute("CREATE TABLE IF NOT EXISTS daily_plans_backup AS SELECT * FROM daily_plans")
        c.execute("CREATE TABLE IF NOT EXISTS proposed_workouts_backup AS SELECT * FROM proposed_workouts")
        c.execute("CREATE TABLE IF NOT EXISTS workout_performance_backup AS SELECT * FROM workout_performance")
        
        # Delete data from tables
        print("Clearing tables...")
        c.execute("DELETE FROM proposed_workouts")
        c.execute("DELETE FROM workout_performance")
        c.execute("DELETE FROM daily_plans")
        
        # Reset the auto-increment counters
        c.execute("DELETE FROM sqlite_sequence WHERE name IN ('daily_plans', 'proposed_workouts', 'workout_performance')")
        
        conn.commit()
        print("All planning tables have been reset.")
        return True
        
    except Exception as e:
        print(f"Error resetting tables: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    confirm = input("This will delete all data in daily_plans, proposed_workouts, and workout_performance tables.\nType 'yes' to confirm: ")
    
    if confirm.lower() == 'yes':
        if reset_planning_tables():
            print("Reset complete.")
        else:
            print("Reset failed.")
    else:
        print("Reset cancelled.")
