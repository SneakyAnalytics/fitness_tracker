#!/usr/bin/env python3
"""
Test AI Coach with User Context
"""

print('🧪 Testing Enhanced AI Coach with User Context\n')
print('=' * 80)

from src.utils.ai_coach_engine import AICoachEngine, AIModel
from src.storage.database import WorkoutDatabase

# Initialize
coach = AICoachEngine(model=AIModel.GEMINI_FREE)
db = WorkoutDatabase()

# Get real weekly summary
print('\n1️⃣ Loading real training data (Oct 27 - Nov 2)...')
weekly_summary = db.generate_weekly_summary('2025-10-27', '2025-11-02')
print(f'   TSS: {weekly_summary["total_tss"]}')
print(f'   Sessions: {weekly_summary["sessions_completed"]}')
print(f'   Types: {weekly_summary["workout_types"]}')

# Define user context (what you'd type in the UI)
print('\n2️⃣ Adding user context...')
user_context = {
    'schedule_constraints': '''
    - Tuesday evening: Zwift racing league (7-8:30pm) - first race upcoming
    - Thursday: Heat chamber research session (light activity only after)
    - Saturday: Available for long endurance ride
    - Sunday: Prefer easy recovery or run
    ''',
    'training_focus': '''
    - Building aerobic base for Oregon gravel events in spring
    - Maintaining XC ski fitness through winter
    - Progressive FTP development toward 320W goal
    - Preparing for consistent Tuesday night Zwift racing
    ''',
    'week_feedback': '''
    - VO2 max test went great (60.3, up from 56 earlier)
    - Felt strong during race simulation workout
    - Nearly cramped on Friday - need better fueling strategy
    - Easy run on Sunday felt smooth with nose breathing
    - Overall energy good, sleep quality solid (4.1/5 avg)
    '''
}

print('   Schedule constraints: Set ✅')
print('   Training focus: Set ✅')
print('   Week feedback: Set ✅')

# Run analysis with user context
print('\n3️⃣ Running AI analysis with user context...')
analysis, metadata = coach.analyze_week(weekly_summary, user_context=user_context)

print(f'\n   Analysis: {len(analysis)} chars')
print(f'   Cost: ${metadata.get("cost", 0):.4f}')

# Check if user context appears in analysis
has_race_ref = 'race' in analysis.lower() or 'zwift' in analysis.lower()
has_vo2_ref = 'vo2' in analysis.lower() or '60.3' in analysis
has_chamber_ref = 'chamber' in analysis.lower() or 'thursday' in analysis.lower()

print('\n📊 Context Integration Check:')
print(f'   Race reference found: {"✅" if has_race_ref else "❌"}')
print(f'   VO2 test reference found: {"✅" if has_vo2_ref else "❌"}')
print(f'   Schedule constraint reference: {"✅" if has_chamber_ref else "❌"}')

# Print sample of analysis
print('\n📝 Analysis Sample (first 800 chars):')
print('-' * 80)
print(analysis[:800])
print('...')
print('-' * 80)

# Now generate plan with same context
print('\n4️⃣ Generating workout plan with user context...')
workout_plan, gen_metadata = coach.generate_workout_plan(
    weekly_summary, 
    analysis,
    user_context=user_context
)

print(f'\n   Plan generated: {workout_plan.get("weekNumber")} week')
print(f'   FTP: {workout_plan.get("ftp")}W')
print(f'   TSS target: {workout_plan.get("plannedTSS")}')
print(f'   Days: {len(workout_plan.get("days", []))}')
print(f'   Cost: ${gen_metadata.get("cost", 0):.4f}')

# Check if Tuesday has appropriate workout (race day)
tuesday = workout_plan.get('days', [])[1] if len(workout_plan.get('days', [])) > 1 else None
if tuesday:
    tuesday_workouts = tuesday.get('workouts', [])
    print(f'\n📅 Tuesday Check (Race Day):')
    if tuesday_workouts:
        for w in tuesday_workouts:
            print(f'   - {w.get("type")}: {w.get("name")}')
    else:
        print('   - Rest day (appropriate before first race)')

print('\n✅ ENHANCED SYSTEM TEST COMPLETE!')
print(f'\n💰 Total cost: ${metadata.get("cost", 0) + gen_metadata.get("cost", 0):.4f}')
