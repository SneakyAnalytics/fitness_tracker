"""
Test AI analysis with interval-by-interval data
"""
from dotenv import load_dotenv
load_dotenv()

import sqlite3
from src.utils.fit_file_analyzer import FitFileAnalyzer

# Get a workout that has an analysis already
conn = sqlite3.connect('data/fitness_data.db')
c = conn.cursor()

# Get workout with analysis
c.execute('''
    SELECT ff.id, ff.workout_day, wa.analysis_text
    FROM fit_files ff
    JOIN workout_analyses wa ON wa.fit_file_id = ff.id
    WHERE ff.workout_day >= '2025-11-17'
    ORDER BY ff.workout_day
    LIMIT 1
''')

result = c.fetchone()
if result:
    fit_id, workout_day, analysis = result
    print(f'Found existing analysis for {workout_day} (ID: {fit_id})')
    print(f'\nAnalysis length: {len(analysis)} characters')
    print(f'\nFirst 500 chars:\n{analysis[:500]}...')
    print(f'\n{"="*60}\n')
    
    # Check if it contains interval-by-interval data
    if 'Minutes 0-' in analysis or 'Warmup (' in analysis:
        print('✓ Analysis contains interval-by-interval execution data!')
    else:
        print('✗ Analysis does NOT contain interval-by-interval data')
        print('\nSearching for interval markers...')
        markers = ['interval', 'prescribed', 'actual', 'execution']
        for marker in markers:
            count = analysis.lower().count(marker)
            print(f'  "{marker}": {count} occurrences')
else:
    print('No analyzed workouts found')
    print('\nLet me check if there are any fit_files at all...')
    c.execute('SELECT COUNT(*) FROM fit_files WHERE workout_day >= "2025-11-17"')
    count = c.fetchone()[0]
    print(f'FIT files from Nov 17+: {count}')

conn.close()
