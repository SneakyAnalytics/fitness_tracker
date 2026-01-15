#!/bin/bash
# Sync .zwo files from Beelink to Mac's Zwift folder

set -e

BEELINK_IP="<beelink-ip>"
BEELINK_USER="<user>"
MAC_ZWIFT_DIR="/Users/<you>/Documents/Zwift/Workouts/6870291"

echo "🔄 Syncing Zwift workout files from Beelink to Mac..."

# Create a temporary directory on Beelink if it doesn't exist
ssh ${BEELINK_USER}@${BEELINK_IP} "if not exist C:\\Users\\<user>\\zwift_workouts mkdir C:\\Users\\<user>\\zwift_workouts" 2>/dev/null

# Sync any .zwo files from the shareable folder on Beelink
echo "📦 Downloading .zwo files..."
scp -r ${BEELINK_USER}@${BEELINK_IP}:C:/Users/<user>/fitness_tracker/shareable/zwift_workouts/* "${MAC_ZWIFT_DIR}/" 2>/dev/null || echo "No files in shareable folder"

echo "✅ Sync complete! Check your Zwift folder for new workouts."
