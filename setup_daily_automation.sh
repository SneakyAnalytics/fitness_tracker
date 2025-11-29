#!/bin/bash

# Setup script for Daily Fitness Tracker Automation
# This configures a launchd agent to run the sync script every night at 10 PM

# Configuration
USER_NAME="jacobrobinson"
PROJECT_DIR="/Users/$USER_NAME/fitness_tracker"
PYTHON_EXEC="$PROJECT_DIR/venv/bin/python"
PLIST_NAME="com.jacobrobinson.fitnesstracker.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="$PROJECT_DIR/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Create the plist file
cat > "$PLIST_PATH" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jacobrobinson.fitnesstracker</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_EXEC</string>
        <string>-m</string>
        <string>src.utils.daily_auto_sync_and_analyze</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONPATH</key>
        <string>$PROJECT_DIR</string>
    </dict>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>22</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>$LOG_DIR/daily_automation.out</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/daily_automation.err</string>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
PLIST_EOF

echo "✅ Created launchd plist at $PLIST_PATH"

# Unload if already loaded (ignore error if not loaded)
launchctl unload "$PLIST_PATH" 2>/dev/null

# Load the new plist
launchctl load "$PLIST_PATH"

echo "✅ Loaded launchd agent"
echo "📅 Scheduled to run daily at 10:00 PM"
echo "⚠️  IMPORTANT: Your computer must be awake for this to run!"
echo "   If your laptop is closed, it may not run unless plugged in with 'Prevent automatic sleeping' enabled."
