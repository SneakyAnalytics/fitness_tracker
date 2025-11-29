#!/usr/bin/env python3
"""
Test saving AI-generated workout plan to database and generating Zwift files
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.ai_coach_engine import AICoachEngine, AIModel
from storage.database import WorkoutDatabase

print("=" * 80)
print("  🧪 TESTING AI PLAN SAVE TO DATABASE + ZWIFT GENERATION")
print("=" * 80)

# Create a sample AI-generated plan (simplified version)
# Using Week 999 starting Dec 1, 2025 to avoid any conflicts with real training data
sample_plan = {
    "weekNumber": 999,  # Use very high number to absolutely avoid conflicts
    "startDate": "2025-12-01",  # Future week - won't interfere with current training
    "ftp": 300,
    "plannedTSS": "350-400",
    "notes": "⚠️ TEST WEEK ONLY - AI coach integration test - SAFE TO DELETE",
    "days": [
        {
            "type": "bike",
            "name": "Recovery Spin",
            "duration": 45,
            "tss": 30,
            "rpe": 2,
            "focus": "Active recovery",
            "description": "Easy spin to flush legs",
            "intervals": [
                {"duration": 5, "power": 150, "description": "Warmup"},
                {"duration": 35, "power": 180, "description": "Steady endurance"},
                {"duration": 5, "power": 150, "description": "Cooldown"}
            ]
        },
        {
            "type": "bike",
            "name": "Threshold Intervals",
            "duration": 75,
            "tss": 85,
            "rpe": 7,
            "focus": "FTP development",
            "description": "4x10min @ threshold",
            "intervals": [
                {"duration": 10, "power": 150, "description": "Warmup"},
                {"duration": 10, "power": 285, "description": "Threshold interval 1"},
                {"duration": 5, "power": 150, "description": "Recovery"},
                {"duration": 10, "power": 285, "description": "Threshold interval 2"},
                {"duration": 5, "power": 150, "description": "Recovery"},
                {"duration": 10, "power": 285, "description": "Threshold interval 3"},
                {"duration": 5, "power": 150, "description": "Recovery"},
                {"duration": 10, "power": 285, "description": "Threshold interval 4"},
                {"duration": 10, "power": 150, "description": "Cooldown"}
            ]
        },
        {
            "type": "run",
            "name": "Easy Run",
            "duration": 40,
            "tss": 35,
            "rpe": 3,
            "focus": "Aerobic base",
            "description": "Easy nose-breathing run",
            "intervals": []
        },
        {
            "type": "bike",
            "name": "Endurance Ride",
            "duration": 90,
            "tss": 75,
            "rpe": 5,
            "focus": "Aerobic endurance",
            "description": "Steady zone 2 ride",
            "intervals": [
                {"duration": 10, "power": 150, "description": "Warmup"},
                {"duration": 70, "power": 200, "description": "Endurance"},
                {"duration": 10, "power": 150, "description": "Cooldown"}
            ]
        },
        {
            "type": "strength",
            "name": "Full Body Strength",
            "duration": 60,
            "tss": 40,
            "rpe": 6,
            "focus": "General strength",
            "description": "Compound movements focus",
            "intervals": []
        },
        {
            "type": "bike",
            "name": "Long Ride",
            "duration": 120,
            "tss": 95,
            "rpe": 6,
            "focus": "Endurance building",
            "description": "Progressive long ride",
            "intervals": [
                {"duration": 15, "power": 150, "description": "Warmup"},
                {"duration": 90, "power": 210, "description": "Endurance pace"},
                {"duration": 15, "power": 150, "description": "Cooldown"}
            ]
        },
        {
            "type": "mobility",
            "name": "Yoga & Stretching",
            "duration": 30,
            "tss": 15,
            "rpe": 2,
            "focus": "Recovery",
            "description": "Active recovery session",
            "intervals": []
        }
    ]
}

print("\n1️⃣ Sample AI plan created")
print(f"   Week: {sample_plan['weekNumber']}")
print(f"   Start Date: {sample_plan['startDate']}")
print(f"   FTP: {sample_plan['ftp']}W")
print(f"   Workouts: {len(sample_plan['days'])}")
print(f"   Cycling workouts: {sum(1 for d in sample_plan['days'] if d['type'] == 'bike')}")

print("\n2️⃣ Initializing AI Coach Engine...")
coach = AICoachEngine(model=AIModel.GEMINI_FREE)
print("   ✅ Coach initialized")

print("\n3️⃣ Saving plan to database and generating Zwift files...")
success, message, zwift_files = coach.save_plan_to_database(
    workout_plan=sample_plan,
    start_date="2025-12-01"  # Future week - won't overwrite current training
)

print("\n" + "=" * 80)
if success:
    print("✅ SUCCESS!")
    print("=" * 80)
    print(f"\n{message}")
    
    if zwift_files:
        print(f"\n🚴 Generated {len(zwift_files)} Zwift workout files:")
        for zfile in zwift_files:
            print(f"   - {zfile}")
    else:
        print("\nℹ️  No Zwift files generated (expected - only bike workouts generate .zwo files)")
    
    print("\n📋 Verify in database:")
    print("   - Check 'Proposed Workouts' tab in Streamlit")
    print("   - Check Zwift app for new workout files")
    print("   - Week 999 should be visible (Dec 1-7, 2025)")
    print("   ⚠️  This is a TEST WEEK - it will be auto-deleted by this script")
    
else:
    print("❌ FAILED!")
    print("=" * 80)
    print(f"\nError: {message}")

print("\n4️⃣ Cleanup (deleting test week 999)...")
try:
    db = WorkoutDatabase()
    db.delete_weekly_plan_cascade(999)
    print("   ✅ Test week deleted")
except Exception as e:
    print(f"   ⚠️  Cleanup failed: {e}")

print("\n" + "=" * 80)
print("  ✅ TEST COMPLETE")
print("=" * 80)
