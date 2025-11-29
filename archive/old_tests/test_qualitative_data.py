#!/usr/bin/env python3
"""
Test that qualitative data (muscle soreness, fatigue) is included in weekly summary
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from storage.database import WorkoutDatabase

print("=" * 80)
print("  🧪 TESTING QUALITATIVE DATA INTEGRATION")
print("=" * 80)

db = WorkoutDatabase()

# Test with a week that has data (adjust these dates to match your actual data)
test_start = "2025-10-28"  # Week 51 start
test_end = "2025-11-03"    # Week 51 end

print(f"\n1️⃣ Checking qualitative data for {test_start} to {test_end}")
qual_data = db.get_weekly_summary_qualitative_data(test_start, test_end)

if qual_data:
    print("✅ Found qualitative data:")
    if qual_data.get('muscle_soreness_patterns'):
        print(f"\n  🦵 Muscle Soreness:")
        print(f"  {qual_data['muscle_soreness_patterns']}")
    if qual_data.get('general_fatigue_level'):
        print(f"\n  😴 Fatigue Levels:")
        print(f"  {qual_data['general_fatigue_level']}")
else:
    print("ℹ️  No qualitative data found for this week")
    print("   (This is OK - qualitative data is optional)")

print(f"\n2️⃣ Testing generate_weekly_summary() integration")
summary = db.generate_weekly_summary(test_start, test_end)

if summary:
    print("✅ Weekly summary generated")
    print(f"\n  📊 Summary includes:")
    print(f"     - Total TSS: {summary.get('total_tss')}")
    print(f"     - Sessions: {summary.get('sessions_completed')}")
    print(f"     - Avg Energy: {summary.get('avg_daily_energy')}")
    print(f"     - Avg Sleep: {summary.get('avg_sleep_quality')}")
    
    # Check if qualitative data is included
    has_soreness = summary.get('muscle_soreness_patterns') is not None
    has_fatigue = summary.get('general_fatigue_level') is not None
    
    print(f"\n  🆕 Qualitative Data Integration:")
    print(f"     - Muscle Soreness: {'✅ INCLUDED' if has_soreness else '❌ Not found'}")
    print(f"     - Fatigue Levels: {'✅ INCLUDED' if has_fatigue else '❌ Not found'}")
    
    if has_soreness or has_fatigue:
        print("\n  🎉 SUCCESS! Qualitative data is now available to AI Coach!")
        
        if has_soreness:
            print(f"\n  📝 Soreness data preview:")
            soreness = summary['muscle_soreness_patterns']
            preview = soreness[:200] + "..." if len(soreness) > 200 else soreness
            print(f"     {preview}")
        
        if has_fatigue:
            print(f"\n  📝 Fatigue data preview:")
            fatigue = summary['general_fatigue_level']
            preview = fatigue[:200] + "..." if len(fatigue) > 200 else fatigue
            print(f"     {preview}")
    else:
        print("\n  ℹ️  No qualitative data for this week (expected if not entered)")
else:
    print("❌ No summary generated (no workout data for this week?)")

print("\n" + "=" * 80)
print("  ✅ TEST COMPLETE")
print("=" * 80)
print("\n📌 What this means:")
print("   - If you've entered muscle soreness or fatigue data in Weekly Summary,")
print("   - the AI Coach will now receive it automatically when analyzing that week")
print("   - The AI can use this to suggest targeted mobility work, adjust recovery,")
print("   - and account for subjective fatigue that might not match device metrics")
print("\n💡 To test with real data:")
print("   1. Go to 'Weekly Summary' tab")
print("   2. Select a week and fill out soreness/fatigue sections")
print("   3. Save the summary")
print("   4. Go to 'AI Coach' tab, select same week")
print("   5. Generate analysis - AI should reference your soreness/fatigue!")
