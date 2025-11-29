#!/bin/bash
# Setup script for automated daily workout analysis

echo "🔧 Setting up automated daily workout analysis..."
echo ""
echo "This will configure your system to automatically analyze workouts every day."
echo ""

# Get the project directory
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH="$PROJECT_DIR/venv/bin/python"

echo "📁 Project directory: $PROJECT_DIR"
echo "🐍 Python path: $PYTHON_PATH"
echo ""

# Test the daily analyzer
echo "🧪 Testing daily analyzer..."
$PYTHON_PATH -c "from src.utils.daily_workout_analyzer import DailyWorkoutAnalyzer; print('✅ Import successful')"

if [ $? -eq 0 ]; then
    echo "✅ Daily analyzer is working!"
else
    echo "❌ Error importing daily analyzer"
    exit 1
fi

echo ""
echo "📝 To set up automatic daily analysis, add this to your crontab:"
echo ""
echo "   # Run at 9 PM every day"
echo "   0 21 * * * cd $PROJECT_DIR && $PYTHON_PATH -m src.utils.daily_workout_analyzer"
echo ""
echo "To edit your crontab, run: crontab -e"
echo ""
echo "Or run manually anytime with:"
echo "   cd $PROJECT_DIR && $PYTHON_PATH -m src.utils.daily_workout_analyzer"
echo ""
echo "✅ Setup complete!"
