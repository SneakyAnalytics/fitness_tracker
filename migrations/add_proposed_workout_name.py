"""
Add proposed_workout_name column to workouts table
This stores the AI-matched proposed workout name for multi-workout days
"""
import sqlite3
from pathlib import Path

def migrate():
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "fitness_data.db"
    
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    try:
        # Check if column already exists
        c.execute("PRAGMA table_info(workouts)")
        columns = [row[1] for row in c.fetchall()]
        
        if 'proposed_workout_name' not in columns:
            print("Adding proposed_workout_name column to workouts table...")
            c.execute('''
                ALTER TABLE workouts
                ADD COLUMN proposed_workout_name TEXT
            ''')
            conn.commit()
            print("✅ Migration complete")
        else:
            print("ℹ️  Column already exists")
    
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
