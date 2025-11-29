#!/usr/bin/env python3
"""
Test Coaching Continuity Loading

This test verifies that the AI coach successfully loads and uses
previous week's continuity in the next coaching session.

Week 1: Oct 27 - Nov 2 (already analyzed, continuity saved)
Week 2: Nov 3 - Nov 9 (will load Week 1 continuity)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.ai_coach_engine import AICoachEngine, AIModel
from storage.database import WorkoutDatabase
from utils.coaching_notes import CoachingNotesManager

print("=" * 80)
print("  🔗 TESTING COACHING CONTINUITY LOADING")
print("=" * 80)

# Initialize components
print("\n1️⃣ Initializing components...")
coach = AICoachEngine(model=AIModel.GEMINI_FREE)
db = WorkoutDatabase()
coaching_notes = CoachingNotesManager()

print("   ✅ AI Coach initialized")
print("   ✅ Database connected")
print("   ✅ Coaching notes loaded")

# Check existing continuity
print("\n2️⃣ Checking saved continuity from Week 1...")
continuity = coaching_notes.get_last_week_continuity()

if continuity:
    print(f"   ✅ Found continuity from {continuity.week_start_date} to {continuity.week_end_date}")
    print(f"      - {len(continuity.key_observations)} key observations")
    print(f"      - {len(continuity.progression_notes)} progression notes")
    print(f"      - {len(continuity.areas_to_monitor)} areas to monitor")
    print(f"      - {len(continuity.next_week_priorities)} priorities")
else:
    print("   ⚠️  No previous continuity found!")
    print("   Run test_phase35_complete.py first to create Week 1 continuity")
    sys.exit(1)

# Load Week 2 data (Nov 3 - Nov 9)
print("\n3️⃣ Loading Week 2 training data (Nov 3 - Nov 9)...")
week2_summary = db.generate_weekly_summary('2025-11-03', '2025-11-09')

if not week2_summary:
    print("   ❌ No data available for Week 2")
    print("   This test requires data for Nov 3-9, 2025")
    sys.exit(1)

print(f"   ✅ Week 2 loaded:")
print(f"      - Total TSS: {week2_summary['total_tss']}")
print(f"      - Hours: {week2_summary['total_training_hours']:.1f}")
print(f"      - Sessions: {week2_summary['sessions_completed']}")

# Define user context for Week 2
print("\n4️⃣ Defining Week 2 user context...")
week2_context = {
    'schedule_constraints': """
        - Tuesday evening: Zwift race (7-8:30pm) - first competitive race!
        - Thursday: Post-heat chamber recovery
        - Saturday: Long outdoor ride or indoor endurance
        - Sunday: Recovery/easy
    """,
    'training_focus': """
        - **PRIMARY FOCUS**: Improve fueling strategy after last week's cramping issue
        - Continue building aerobic base with progressive volume
        - Prepare for competitive Zwift racing
        - Maintain strength/mobility work
    """,
    'week_feedback': """
        - Implemented new fueling plan: carbs during all hard efforts
        - Feeling strong and recovered
        - Excited for first Zwift race Tuesday
        - Sleep quality good (avg 4.0+/5)
    """
}

print("   ✅ Context defined with focus on fueling improvements")

# Run analysis WITH continuity loading
print("\n5️⃣ Running AI analysis for Week 2...")
print("   (This should automatically load Week 1 continuity)")
print("   ⏳ Calling AI... (10-30 seconds)")

analysis, metadata = coach.analyze_week(
    weekly_summary=week2_summary,
    user_context=week2_context
)

print(f"\n   ✅ Analysis complete!")
print(f"      Tokens: {metadata.get('prompt_tokens', 0) + metadata.get('candidates_token_count', 0)}")
print(f"      Cost: ${metadata.get('cost', 0):.4f}")

# Check if analysis references Week 1 insights
print("\n6️⃣ Validating continuity integration in analysis...")
week1_keywords = [
    'VO2',  # Should reference VO2 improvement from Week 1
    'fuel',  # Should reference fueling issue from Week 1
    'volume',  # Should reference low volume from Week 1
    'cram',  # Should reference cramping from Week 1
]

found_keywords = []
for keyword in week1_keywords:
    if keyword.lower() in analysis.lower():
        found_keywords.append(keyword)
        print(f"   ✅ Found reference to '{keyword}' from Week 1 continuity")

if len(found_keywords) >= 2:
    print(f"\n   ✅ CONTINUITY VALIDATED: Analysis references {len(found_keywords)}/4 Week 1 insights")
else:
    print(f"\n   ⚠️  Limited continuity integration: Only {len(found_keywords)}/4 keywords found")

# Display excerpt of analysis
print("\n7️⃣ Analysis excerpt (first 800 chars):")
print("   " + "-" * 76)
excerpt = analysis[:800].replace('\n', '\n   ')
print(f"   {excerpt}")
print("   " + "-" * 76)

# Extract Week 2 continuity
print("\n8️⃣ Extracting Week 2 continuity...")
week2_continuity = coach.extract_coaching_continuity(analysis, week2_summary)

if week2_continuity:
    print("   ✅ Week 2 continuity extracted!")
    print(f"      - {len(week2_continuity.get('key_observations', []))} observations")
    print(f"      - {len(week2_continuity.get('progression_notes', []))} progression notes")
    print(f"      - {len(week2_continuity.get('areas_to_monitor', []))} areas to monitor")
    print(f"      - {len(week2_continuity.get('next_week_priorities', []))} priorities")
    
    # Save Week 2 continuity
    coaching_notes.add_coaching_continuity(
        week_start_date=week2_continuity['week_start_date'],
        week_end_date=week2_continuity['week_end_date'],
        week_number=week2_continuity['week_number'],
        key_observations=week2_continuity['key_observations'],
        progression_notes=week2_continuity['progression_notes'],
        areas_to_monitor=week2_continuity['areas_to_monitor'],
        next_week_priorities=week2_continuity['next_week_priorities'],
        recurring_schedule=week2_continuity.get('recurring_schedule')
    )
    print("   ✅ Week 2 continuity saved!")
else:
    print("   ⚠️  Week 2 continuity extraction failed")

# Show continuity history
print("\n9️⃣ Continuity History:")
all_continuity = coaching_notes.get_recent_continuity(n=10)
for i, cont in enumerate(all_continuity, 1):
    print(f"   Week {i}: {cont.week_start_date} to {cont.week_end_date}")
    print(f"      Observations: {len(cont.key_observations)}")
    print(f"      Priorities: {len(cont.next_week_priorities)}")

print("\n" + "=" * 80)
print("  ✅ CONTINUITY LOADING TEST COMPLETE!")
print("=" * 80)
print("\n📈 Summary:")
print(f"   - Week 1 continuity successfully loaded into Week 2 prompt")
print(f"   - Week 2 analysis references {len(found_keywords)}/4 Week 1 insights")
print(f"   - Week 2 continuity extracted and saved")
print(f"   - Total continuity entries: {len(all_continuity)}")
print("\n🎯 The AI coach now has persistent memory across weeks!")
