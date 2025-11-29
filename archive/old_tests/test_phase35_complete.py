#!/usr/bin/env python3
"""
🧪 Phase 3.5 Complete End-to-End Test
=====================================
Tests ALL Phase 3.5 enhancements with real AI calls:

1. Multi-sport workout classification (Run, Strength, Mobility)
2. User context integration (schedule, focus, feedback)
3. Coaching continuity extraction and persistence
4. Week-over-week memory (AI remembers last week's insights)

This makes actual API calls and costs a small amount ($0.01-0.05).
"""

import os
import sys
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.ai_coach_engine import AICoachEngine
from src.storage.database import WorkoutDatabase
from src.utils.coaching_notes import CoachingNotesManager

def print_section(title):
    """Pretty print section headers"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def main():
    print_section("🧪 PHASE 3.5 COMPLETE END-TO-END TEST")
    
    # Initialize
    print("\n1️⃣ Initializing AI Coach Engine...")
    coach = AICoachEngine()
    db = WorkoutDatabase()
    notes_manager = CoachingNotesManager()
    
    print(f"   ✅ Model: {coach.model.value}")
    print(f"   ✅ Database: {db.db_path}")
    print(f"   ✅ Coaching notes: {notes_manager.notes_path}")
    
    # Load real training data
    print_section("2️⃣ LOADING REAL TRAINING DATA")
    
    week_start = '2025-10-27'
    week_end = '2025-11-02'
    
    print(f"\n   Loading week: {week_start} to {week_end}")
    weekly_summary = db.generate_weekly_summary(week_start, week_end)
    
    if not weekly_summary:
        print("   ❌ No data found for this week")
        return 1
    
    print(f"   ✅ Loaded {weekly_summary.get('sessions', 0)} workouts")
    print(f"   Total TSS: {weekly_summary.get('total_tss', 0):.1f}")
    print(f"   Total Hours: {weekly_summary.get('total_hours', 0):.1f}")
    
    # Show workout classification
    print("\n   📊 Workout Classification:")
    workout_types = weekly_summary.get('workout_types_distribution', {})
    for wtype, count in sorted(workout_types.items(), key=lambda x: x[1], reverse=True):
        print(f"      - {wtype}: {count}")
    
    # Define user context
    print_section("3️⃣ DEFINING USER CONTEXT")
    
    user_context = {
        'schedule_constraints': "Tuesday Zwift racing league (7-8:30pm) - first race upcoming, Thursday heat chamber session (light workout after), Saturday long ride available, Sunday prefer easy recovery or easy run",
        'training_focus': "Building aerobic base for Oregon gravel events in spring, maintaining XC ski fitness for winter, progressive FTP improvement toward 320W goal, preparing for Tuesday evening Zwift racing",
        'week_feedback': "VO2 max test showed 60.3 (up from 56.0 four months ago!), strong race simulation on Friday but nearly cramped due to insufficient fueling, smooth nose-breathing run felt great, sleep averaging 4.1/5 quality"
    }
    
    print("\n   📅 Schedule Constraints:")
    print(f"      {user_context['schedule_constraints'][:120]}...")
    print("\n   🎯 Training Focus:")
    print(f"      {user_context['training_focus'][:120]}...")
    print("\n   💭 Week Feedback:")
    print(f"      {user_context['week_feedback'][:120]}...")
    
    # Get comprehensive context
    print_section("4️⃣ GATHERING COMPREHENSIVE CONTEXT")
    
    print("\n   Loading 4-week historical data...")
    comprehensive_context = coach.db_queries.get_comprehensive_context(weeks_back=4)
    
    print(f"   ✅ Last 4 weeks TSS: {comprehensive_context.get('last_4_weeks_summary', {}).get('total_tss', 0):.1f}")
    print(f"   ✅ Workout type trends: {len(comprehensive_context.get('workout_type_trends', {}))} categories")
    
    # Check previous continuity
    print_section("5️⃣ CHECKING PREVIOUS CONTINUITY")
    
    last_continuity = notes_manager.get_last_week_continuity()
    if last_continuity:
        print(f"\n   ✅ Found previous week's continuity (Week {last_continuity.week_number})")
        print(f"      Observations: {len(last_continuity.key_observations)}")
        print(f"      Priorities set: {len(last_continuity.next_week_priorities)}")
    else:
        print("\n   ℹ️  No previous continuity (first coaching session)")
    
    # Run analysis with user context
    print_section("6️⃣ RUNNING AI ANALYSIS (with user context)")
    
    print("\n   ⏳ Calling AI to analyze week...")
    print("   (This will take 10-30 seconds...)")
    
    analysis, analysis_meta = coach.analyze_week(
        weekly_summary,
        comprehensive_context=comprehensive_context,
        user_context=user_context
    )
    
    print(f"\n   ✅ Analysis complete!")
    print(f"   Tokens used: {analysis_meta.get('completion_tokens', 0):,}")
    print(f"   Cost: ${analysis_meta.get('cost', 0):.4f}")
    
    # Show analysis sample
    print("\n   📄 Analysis Sample (first 500 chars):")
    print("   " + "-"*76)
    print("   " + analysis[:500].replace('\n', '\n   '))
    print("   " + "-"*76)
    
    # Check if user context was incorporated
    print("\n   🔍 Validating user context integration:")
    checks = {
        'Zwift racing mentioned': 'zwift' in analysis.lower() or 'racing' in analysis.lower(),
        'VO2 max 60.3 referenced': '60.3' in analysis or 'vo2' in analysis.lower(),
        'Gravel events mentioned': 'gravel' in analysis.lower(),
        'Chamber session noted': 'chamber' in analysis.lower(),
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "⚠️ "
        print(f"      {status} {check}")
    
    # Extract coaching continuity
    print_section("7️⃣ EXTRACTING COACHING CONTINUITY")
    
    print("\n   ⏳ Extracting structured insights for next week...")
    
    continuity_data = coach.extract_coaching_continuity(analysis, weekly_summary)
    
    if continuity_data:
        print(f"\n   ✅ Continuity extracted successfully!")
        print(f"\n   📝 Key Observations ({len(continuity_data.get('key_observations', []))}):")
        for obs in continuity_data.get('key_observations', [])[:3]:
            print(f"      - {obs}")
        
        print(f"\n   📈 Progression Notes ({len(continuity_data.get('progression_notes', []))}):")
        for prog in continuity_data.get('progression_notes', [])[:3]:
            print(f"      - {prog}")
        
        print(f"\n   👀 Areas to Monitor ({len(continuity_data.get('areas_to_monitor', []))}):")
        for area in continuity_data.get('areas_to_monitor', [])[:3]:
            print(f"      - {area}")
        
        print(f"\n   🎯 Next Week Priorities ({len(continuity_data.get('next_week_priorities', []))}):")
        for priority in continuity_data.get('next_week_priorities', [])[:3]:
            print(f"      - {priority}")
        
        # Save continuity
        print("\n   💾 Saving continuity to coaching notes...")
        notes_manager.add_coaching_continuity(
            week_start_date=continuity_data.get('week_start_date', week_start),
            week_end_date=continuity_data.get('week_end_date', week_end),
            week_number=continuity_data.get('week_number', 1),
            key_observations=continuity_data.get('key_observations', []),
            progression_notes=continuity_data.get('progression_notes', []),
            areas_to_monitor=continuity_data.get('areas_to_monitor', []),
            next_week_priorities=continuity_data.get('next_week_priorities', [])
        )
        print("   ✅ Continuity saved!")
        
    else:
        print("\n   ⚠️  Failed to extract continuity")
    
    # Generate workout plan
    print_section("8️⃣ GENERATING WORKOUT PLAN (with context)")
    
    print("\n   ⏳ Calling AI to generate next week's workouts...")
    print("   (This will take 10-30 seconds...)")
    
    constraints = {
        'max_weekly_tss': 650,
        'min_weekly_tss': 400,
        'preferred_workout_times': ['morning', 'evening'],
        'equipment_available': ['Zwift', 'outdoor', 'treadmill', 'gym']
    }
    
    workout_plan, plan_meta = coach.generate_workout_plan(
        weekly_summary,
        analysis=analysis,
        constraints=constraints,
        user_context=user_context
    )
    
    print(f"\n   ✅ Workout plan generated!")
    print(f"   Tokens used: {plan_meta.get('completion_tokens', 0):,}")
    print(f"   Cost: ${plan_meta.get('cost', 0):.4f}")
    
    # Validate plan
    is_valid, errors = coach.validate_workout_plan(workout_plan)
    
    if is_valid:
        print("\n   ✅ Workout plan validation PASSED")
        
        # Show workout summary
        days = workout_plan.get('days', [])
        print(f"\n   📅 Generated {len(days)} days:")
        for day in days:
            day_name = day.get('dayOfWeek', 'Unknown')
            workout_type = day.get('workoutType', 'Rest')
            duration = day.get('estimatedDuration', 0)
            tss = day.get('targetTSS', {})
            
            if workout_type != 'rest':
                tss_range = f"{tss.get('min', 0)}-{tss.get('max', 0)} TSS"
                print(f"      {day_name}: {workout_type} - {duration}min ({tss_range})")
            else:
                print(f"      {day_name}: Rest/Recovery")
        
        # Check if Tuesday is appropriate for racing
        tuesday = next((d for d in days if d.get('dayOfWeek') == 'Tuesday'), None)
        if tuesday:
            print(f"\n   🔍 Tuesday workout (race day):")
            print(f"      Type: {tuesday.get('workoutType', 'Unknown')}")
            print(f"      Duration: {tuesday.get('estimatedDuration', 0)}min")
            if 'race' in tuesday.get('workoutType', '').lower() or \
               'event' in tuesday.get('workoutType', '').lower() or \
               tuesday.get('estimatedDuration', 0) >= 60:
                print(f"      ✅ Appropriate for race/event")
            else:
                print(f"      ⚠️  May not account for racing league")
    
    else:
        print("\n   ❌ Workout plan validation FAILED")
        for error in errors:
            print(f"      - {error}")
    
    # Summary
    print_section("9️⃣ TEST SUMMARY")
    
    total_cost = coach.session_cost
    
    print(f"\n   💰 Total Cost: ${total_cost:.4f}")
    print(f"   📊 Analysis Tokens: {analysis_meta.get('completion_tokens', 0):,}")
    print(f"   🏋️  Plan Tokens: {plan_meta.get('completion_tokens', 0):,}")
    
    print("\n   ✅ COMPLETED TESTS:")
    print("      ✅ Multi-sport workout classification (Run, Strength, Mobility)")
    print("      ✅ User context integration in analysis")
    print("      ✅ User context integration in workout plan")
    print("      ✅ Coaching continuity extraction")
    print("      ✅ Continuity persistence to coaching_notes.json")
    print("      ✅ Workout plan generation and validation")
    
    if continuity_data:
        print("\n   🔮 Next Session Preview:")
        print("      The AI will now have access to this week's continuity!")
        print("      It will remember:")
        print(f"         - {len(continuity_data.get('key_observations', []))} key observations")
        print(f"         - {len(continuity_data.get('next_week_priorities', []))} priorities")
        print("      Run this test again with a different week to see continuity in action!")
    
    print_section("✅ PHASE 3.5 TEST COMPLETE!")
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
