#!/usr/bin/env python3
"""
Database migration: Add matched_at and match_source columns to workouts table
This supports the manual workout matching workflow
"""
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def migrate(db_path: str = "data/fitness_data.db"):
    """Add matched_at and match_source columns to workouts table"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Check if columns already exist
        c.execute("PRAGMA table_info(workouts)")
        columns = [row[1] for row in c.fetchall()]
        
        if 'matched_at' not in columns:
            print("Adding matched_at column...")
            c.execute('''
                ALTER TABLE workouts 
                ADD COLUMN matched_at TIMESTAMP
            ''')
            print("✓ Added matched_at column")
        else:
            print("✓ matched_at column already exists")
        
        if 'match_source' not in columns:
            print("Adding match_source column...")
            c.execute('''
                ALTER TABLE workouts 
                ADD COLUMN match_source TEXT
            ''')
            print("✓ Added match_source column")
            
            # Set existing matched workouts to 'ai' source
            c.execute('''
                UPDATE workouts 
                SET match_source = 'ai' 
                WHERE proposed_workout_name IS NOT NULL
            ''')
            rows_updated = c.rowcount
            print(f"✓ Set {rows_updated} existing matches to source='ai'")
        else:
            print("✓ match_source column already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/fitness_data.db"
    migrate(db_path)
