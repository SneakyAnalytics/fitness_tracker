#!/usr/bin/env python3
"""
One-time script to deduplicate personal_bests table.
Keeps only the oldest entry for each unique effort_type + effort_value combination.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'fitness_data.db'

def deduplicate_personal_bests():
    """Remove duplicate personal best entries"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Find duplicate entries (same athlete_id, effort_type, and effort_value)
        c.execute('''
            SELECT athlete_id, effort_type, effort_value, COUNT(*) as count
            FROM personal_bests
            GROUP BY athlete_id, effort_type, effort_value
            HAVING COUNT(*) > 1
        ''')
        
        duplicates = c.fetchall()
        
        if not duplicates:
            print("No duplicates found!")
            return
        
        print(f"Found {len(duplicates)} duplicate groups:")
        
        deleted_count = 0
        for athlete_id, effort_type, effort_value, count in duplicates:
            print(f"  - {effort_type}: {effort_value}W ({count} entries)")
            
            # Get all IDs for this combination, ordered by id (oldest first)
            c.execute('''
                SELECT id FROM personal_bests
                WHERE athlete_id = ? AND effort_type = ? AND effort_value = ?
                ORDER BY id ASC
            ''', (athlete_id, effort_type, effort_value))
            
            ids = [row[0] for row in c.fetchall()]
            
            # Keep the first (oldest) entry, delete the rest
            ids_to_delete = ids[1:]
            
            for pb_id in ids_to_delete:
                c.execute('DELETE FROM personal_bests WHERE id = ?', (pb_id,))
                deleted_count += 1
        
        print(f"\nDeleted {deleted_count} duplicate entries")
        
        # Now recalculate rankings for all effort types
        c.execute('SELECT DISTINCT athlete_id, effort_type FROM personal_bests')
        effort_types = c.fetchall()
        
        print("\nRecalculating rankings...")
        for athlete_id, effort_type in effort_types:
            # Get all PBs for this type, ordered by value
            c.execute('''
                SELECT id, effort_value
                FROM personal_bests
                WHERE athlete_id = ? AND effort_type = ?
                ORDER BY effort_value DESC
            ''', (athlete_id, effort_type))
            
            all_pbs = c.fetchall()
            
            # Update ranks (1-3 for top 3, NULL for rest)
            for i, (pb_id, pb_value) in enumerate(all_pbs):
                new_rank = i + 1 if i < 3 else None
                c.execute('''
                    UPDATE personal_bests
                    SET rank = ?
                    WHERE id = ?
                ''', (new_rank, pb_id))
            
            # Show top 3 for this effort type
            top_3 = [(val, i+1) for i, (_, val) in enumerate(all_pbs[:3])]
            print(f"  {effort_type}: {', '.join([f'#{rank}: {val}W' for val, rank in top_3])}")
        
        conn.commit()
        print("\n✓ Deduplication complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    deduplicate_personal_bests()
