#!/usr/bin/env python3
"""
Re-save the latest coach chat session plan using the corrected week numbering logic.
Run this inside the Docker container after deploying the fixed ai_coach_engine.py.
"""
import sys
import os
sys.path.insert(0, '/app/src')

import sqlite3
import json

DB_PATH = '/app/data/fitness_data.db'
ZWIFT_DIR = os.getenv('ZWIFT_WORKOUTS_DIR', '/app/shareable/zwift_workouts')

# ── 1. Load the saved plan from coach_chat_sessions ──────────────────────────
conn = sqlite3.connect(DB_PATH)
row = conn.execute(
    "SELECT week_start_date, current_plan FROM coach_chat_sessions ORDER BY updated_at DESC LIMIT 1"
).fetchone()
conn.close()

if not row:
    print("❌ No chat session found in DB")
    sys.exit(1)

week_start_date, plan_json = row
plan = json.loads(plan_json)
print(f"✅ Loaded plan for week starting {week_start_date}")
print(f"   AI weekNumber in plan: {plan.get('weekNumber')}  startDate: {plan.get('startDate')}")

# ── 2. Delete the wrongly-numbered Week_11 entry that was created earlier ───
conn = sqlite3.connect(DB_PATH)
bad_row = conn.execute(
    "SELECT weekNumber FROM weekly_plans WHERE startDate = ?", (plan.get('startDate', week_start_date),)
).fetchone()
conn.close()

if bad_row:
    wrong_num = bad_row[0]
    print(f"   Found existing weekly_plan with weekNumber={wrong_num} — deleting it so the fixed code can assign the correct number")
    from storage.database import WorkoutDatabase
    db = WorkoutDatabase()
    db.delete_weekly_plan_cascade(wrong_num)
    print(f"   ✅ Deleted week {wrong_num}")

# ── 3. Re-save with the fixed engine ────────────────────────────────────────
from utils.ai_coach_engine import AICoachEngine, AIModel
coach = AICoachEngine(model=AIModel.GEMINI_FREE)  # model doesn't matter for save

start_date = plan.get('startDate', week_start_date)
print(f"\n💾 Re-saving plan with start_date={start_date}  zwift_dir={ZWIFT_DIR}")
success, message, zwift_files = coach.save_plan_to_database(
    workout_plan=plan,
    start_date=start_date,
    output_dir=ZWIFT_DIR,
)

if success:
    print(f"\n✅ {message}")
    if zwift_files:
        print(f"\n🚴 Generated {len(zwift_files)} Zwift files:")
        for f in zwift_files:
            print(f"   {f}")
    else:
        print("⚠️  No Zwift files generated")
else:
    print(f"\n❌ Save failed: {message}")
    sys.exit(1)
