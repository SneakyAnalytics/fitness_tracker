#!/bin/bash
# Sync .zwo files from Beelink to Mac's Zwift folder

set -e

BEELINK_IP="100.117.194.8"
BEELINK_USER="rakej"
MAC_ZWIFT_DIR="/Users/jacobrobinson/Documents/Zwift/Workouts/6870291"

echo "🔄 Syncing Zwift workout files from Beelink to Mac..."

# Create a temporary directory on Beelink if it doesn't exist
ssh ${BEELINK_USER}@${BEELINK_IP} "if not exist C:\\Users\\rakej\\zwift_workouts mkdir C:\\Users\\rakej\\zwift_workouts" 2>/dev/null

# Sync any .zwo files from the shareable folder on Beelink
echo "📦 Downloading .zwo files..."
scp -r ${BEELINK_USER}@${BEELINK_IP}:C:/Users/rakej/fitness_tracker/shareable/zwift_workouts/* "${MAC_ZWIFT_DIR}/" 2>/dev/null || echo "No files in shareable folder"

echo "✅ Sync complete! Check your Zwift folder for new workouts."
