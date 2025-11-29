"""
Test AI analysis by re-downloading and analyzing a real workout from TrainingPeaks
"""
from dotenv import load_dotenv
load_dotenv()

from datetime import date
from src.utils.daily_auto_sync_and_analyze import DailyAutoSyncAndAnalyze

# Target the Nov 20 threshold workout
target_date = date(2025, 11, 20)

print(f"Testing AI analysis with real workout from {target_date}")
print("=" * 60)

automation = DailyAutoSyncAndAnalyze()

# Run the full automation for that date
results = automation.run_daily_automation(
    target_date=target_date,
    ftp_watts=300,
    cleanup=True  # Clean up temp files after
)

print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print(f"Sync successful: {results['sync_successful']}")
print(f"FIT files downloaded: {results['fit_files_downloaded']}")
print(f"Workouts analyzed: {results['workouts_analyzed']}")
print(f"Personal bests: {results['personal_bests']}")

if results['errors']:
    print(f"\nErrors ({len(results['errors'])}):")
    for error in results['errors']:
        print(f"  - {error}")

# Now check the analysis in the database
if results['workouts_analyzed'] > 0:
    print("\n" + "=" * 60)
    print("CHECKING STORED ANALYSIS")
    print("=" * 60)
    
    import sqlite3
    conn = sqlite3.connect('data/fitness_data.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT wa.analysis_text
        FROM workout_analyses wa
        JOIN fit_files ff ON wa.fit_file_id = ff.id
        WHERE ff.workout_day = ?
        ORDER BY wa.created_at DESC
        LIMIT 1
    ''', (str(target_date),))
    
    result = c.fetchone()
    if result:
        analysis = result[0]
        print(f"\nAnalysis length: {len(analysis)} characters")
        print(f"\nFirst 1000 characters:")
        print("-" * 60)
        print(analysis[:1000])
        print("-" * 60)
        
        # Check for interval-by-interval data markers
        print("\n" + "=" * 60)
        print("INTERVAL DATA CHECK")
        print("=" * 60)
        
        markers = [
            ('Warmup (', 'Warmup interval header'),
            ('Minutes 0-', 'Minute-by-minute breakdown'),
            ('Prescribed:', 'Prescribed power values'),
            ('Actual:', 'Actual execution values'),
            ('18min', 'Main interval duration'),
        ]
        
        found_count = 0
        for marker, description in markers:
            if marker in analysis:
                print(f"✓ Found: {description} ('{marker}')")
                found_count += 1
            else:
                print(f"✗ Missing: {description} ('{marker}')")
        
        print(f"\nInterval data markers found: {found_count}/{len(markers)}")
        
        if found_count >= 3:
            print("\n🎉 SUCCESS! AI analysis contains interval-by-interval execution data!")
        else:
            print("\n⚠️  Analysis may be missing interval execution details")
    else:
        print("\n✗ No analysis found in database")
    
    conn.close()
