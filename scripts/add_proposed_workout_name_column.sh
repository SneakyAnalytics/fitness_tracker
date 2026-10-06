#!/bin/bash
# Add proposed_workout_name column to workouts table if it doesn't exist

cd /home/rakej/fitness_tracker

# Run the Python migration
python3 migrations/add_proposed_workout_name.py

# Restart Docker containers to pick up the change
docker-compose restart

echo "✅ Migration complete and containers restarted"
