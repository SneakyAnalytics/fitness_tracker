#!/bin/bash
set -e

# Print startup info
echo "🚀 Starting Fitness Tracker..."
echo "Working directory: $(pwd)"
echo "Python version: $(python3 --version)"

# Check database exists
if [ -f "data/fitness_data.db" ]; then
    echo "✅ Database found: data/fitness_data.db"
else
    echo "⚠️  Database not found at data/fitness_data.db"
    echo "Creating empty database..."
    # You can add database initialization here if needed
fi

# Check .env file
if [ -f ".env" ]; then
    echo "✅ Environment file loaded"
else
    echo "⚠️  No .env file found - some features may not work"
fi

# Execute the command passed to the container
exec "$@"
