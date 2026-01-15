#!/usr/bin/env python3
"""
Delete workout analyses linked to FIT files with bad TSS values (< 1).
This handles duplicate FIT file entries that were imported with incorrect TSS scaling.
"""

import sqlite3
from pathlib import Path

def main():
    db_path = Path(__file__).parent / 'data' / 'fitness_data.db'
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Find all analyses with bad TSS
    c.execute('''
        SELECT 
            wa.id,
            f.id as fit_file_id,
            f.workout_day,
            f.workout_title,
            CAST(json_extract(f.fit_data, '$.power_metrics.tss') AS REAL) as tss
        FROM workout_analyses wa
        JOIN fit_files f ON wa.fit_file_id = f.id
        WHERE json_extract(f.fit_data, '$.sport') = 'cycling'
          AND CAST(json_extract(f.fit_data, '$.power_metrics.tss') AS REAL) < 1
        ORDER BY f.workout_day DESC
    ''')
    
    bad_analyses = c.fetchall()
    
    if not bad_analyses:
        print("✅ No bad analyses found - all workout analyses have valid TSS!")
        return
    
    print(f"🔍 Found {len(bad_analyses)} analyses with bad TSS (< 1):")
    print()
    
    for analysis_id, fit_id, workout_day, title, tss in bad_analyses:
        print(f"  Analysis {analysis_id}: {workout_day} - {title[:50]}")
        print(f"    FIT ID: {fit_id}, TSS: {tss:.4f}")
    
    print()
    response = input(f"Delete these {len(bad_analyses)} analyses? (y/n): ")
    
    if response.lower() == 'y':
        fit_ids = [row[1] for row in bad_analyses]
        placeholders = ','.join(['?'] * len(fit_ids))
        
        c.execute(f'DELETE FROM workout_analyses WHERE fit_file_id IN ({placeholders})', fit_ids)
        conn.commit()
        
        print(f"✅ Deleted {c.rowcount} workout analyses")
        print()
        print("💡 Run backfill_workout_analyses.py to regenerate analyses with correct FIT files")
    else:
        print("❌ Cancelled - no analyses deleted")
    
    conn.close()

if __name__ == '__main__':
    main()
