#!/usr/bin/env python3
"""
Quick validation test for Phase 3.5 user context enhancements.
Tests prompt construction without calling the AI API.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.ai_coach_engine import AICoachEngine
from src.storage.database import WorkoutDatabase
from src.utils.ai_prompts import PromptContext, AICoachPrompts

def main():
    print("🧪 Quick Validation - User Context Integration\n")
    print("="*80)
    
    # Initialize components
    print("1️⃣ Initializing components...")
    coach = AICoachEngine()
    db = WorkoutDatabase()
    prompt_builder = AICoachPrompts()
    
    # Load real data
    print("\n2️⃣ Loading real training data (Oct 27 - Nov 2)...")
    weekly_summary = db.generate_weekly_summary('2025-10-27', '2025-11-02')
    sessions = weekly_summary.get('sessions') or weekly_summary.get('number_of_daily_workouts', 0)
    print(f"   ✅ Loaded {sessions} workouts")
    print(f"   TSS: {weekly_summary.get('total_tss', 0):.1f}, Hours: {weekly_summary.get('total_hours', 0):.2f}")
    
    # Define user context
    print("\n3️⃣ Defining user context...")
    user_context = {
        'schedule_constraints': "Tuesday Zwift racing league (7-8:30pm) - first race upcoming, Thursday heat chamber (light after), Saturday long ride available, Sunday prefer easy recovery/run",
        'training_focus': "Building aerobic base for Oregon gravel, maintaining XC ski fitness, progressive FTP toward 320W, preparing for Tuesday Zwift racing",
        'week_feedback': "VO2 max 60.3 (up from 56), strong race sim, nearly cramped Friday (fueling issue), smooth nose breathing run, solid sleep 4.1/5"
    }
    print("   ✅ User context defined")
    
    # Build prompt context
    print("\n4️⃣ Building prompt with user context...")
    
    # Create minimal athlete profile and coaching notes
    athlete_profile = {
        'name': 'Jake Robinson',
        'gender': 'Male',
        'age': 32,
        'current_ftp': 296,
        'training_experience': 'Advanced',
        'training_goals': 'Gravel racing, XC skiing',
        'training_availability': 'Flexible with evening preference'
    }
    
    coaching_notes = {
        'recent_observations': []
    }
    
    comprehensive_context = {
        'last_4_weeks_summary': {
            'total_tss': 950,
            'total_hours': 22.5
        }
    }
    
    prompt_context = PromptContext(
        athlete_profile=athlete_profile,
        coaching_notes=coaching_notes,
        weekly_summary=weekly_summary,
        comprehensive_context=comprehensive_context,
        constraints={
            'max_weekly_tss': 650,
            'min_weekly_tss': 400,
            'preferred_workout_times': ['morning', 'evening'],
            'equipment_available': ['Zwift', 'outdoor', 'treadmill']
        },
        user_context=user_context  # NEW: User context parameter
    )
    
    # Generate analysis prompt
    analysis_prompt = prompt_builder.build_weekly_analysis_prompt(prompt_context)
    
    # Validate context integration
    print("\n5️⃣ Validating user context integration in prompt...")
    
    validation_checks = {
        'Has user context section': "Athlete's Weekly Context" in analysis_prompt,
        'Has schedule constraints': 'Tuesday Zwift racing' in analysis_prompt or 'zwift racing' in analysis_prompt.lower(),
        'Has training focus': 'Oregon gravel' in analysis_prompt or 'gravel' in analysis_prompt.lower(),
        'Has week feedback': 'VO2 max 60.3' in analysis_prompt or '60.3' in analysis_prompt,
        'Has chamber reference': 'chamber' in analysis_prompt.lower(),
        'Has context directive': 'Factor this athlete input' in analysis_prompt,
    }
    
    all_passed = True
    for check_name, result in validation_checks.items():
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 SUCCESS: All user context validations passed!")
    else:
        print("\n⚠️  FAILURE: Some validations failed")
        return 1
    
    # Show prompt structure
    print("\n6️⃣ Prompt structure overview:")
    print(f"   Total prompt length: {len(analysis_prompt):,} characters")
    print(f"   Estimated tokens: ~{len(analysis_prompt) // 4:,}")
    
    # Extract and display user context section
    print("\n7️⃣ User context section in prompt:")
    if "Athlete's Weekly Context" in analysis_prompt:
        start_idx = analysis_prompt.index("Athlete's Weekly Context")
        # Find next major section or end
        next_section_markers = ['\n## Task:', '\n## Training Analysis', '\n## Workout', '\n---', '\n# Training Data']
        end_idx = len(analysis_prompt)
        for marker in next_section_markers:
            try:
                marker_idx = analysis_prompt.index(marker, start_idx + 1)
                if marker_idx < end_idx:
                    end_idx = marker_idx
            except ValueError:
                continue
        
        user_context_section = analysis_prompt[start_idx:end_idx].strip()
        print("-" * 80)
        print(user_context_section[:800])  # First 800 chars
        print("-" * 80)
    
    # Test generation prompt too
    print("\n8️⃣ Testing workout generation prompt...")
    mock_analysis = "Sample analysis content for testing"
    generation_prompt = prompt_builder.build_workout_generation_prompt(prompt_context, mock_analysis)
    
    gen_validation_checks = {
        'Has user context section': "Athlete's Weekly Context" in generation_prompt,
        'Has schedule constraints': 'Tuesday Zwift racing' in generation_prompt or 'zwift racing' in generation_prompt.lower(),
        'Has training focus': 'Oregon gravel' in generation_prompt or 'gravel' in generation_prompt.lower(),
    }
    
    gen_passed = all(gen_validation_checks.values())
    for check_name, result in gen_validation_checks.items():
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}")
    
    if gen_passed:
        print("\n🎉 SUCCESS: Generation prompt also includes user context!")
    else:
        print("\n⚠️  FAILURE: Generation prompt missing user context")
        return 1
    
    print("\n" + "="*80)
    print("✅ PHASE 3.5 VALIDATION COMPLETE - User context integration working!")
    print("="*80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
