#!/bin/bash
# Sync .zwo files from Beelink to Mac's Zwift folder

set -e

BEELINK_IP="100.117.194.8"
BEELINK_USER="rakej"
MAC_ZWIFT_DIR="/Users/jacobrobinson/Documents/Zwift/Workouts/6870291"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15"
SOURCE_CONTAINER="fitness-tracker-api"

echo "🔄 Syncing Zwift workout files from Beelink to Mac..."

# Determine latest Week_* folder from the live Docker shareable volume
LATEST_WEEK=$(ssh $SSH_OPTS ${BEELINK_USER}@${BEELINK_IP} \
  "docker exec ${SOURCE_CONTAINER} python3 -c \"import os,re; p='/app/shareable/zwift_workouts'; ws=sorted([d for d in os.listdir(p) if re.match(r'^Week_[0-9]+$', d)], key=lambda x:int(x.split('_')[1])); print(ws[-1] if ws else '')\"" \
  | tr -d '\r')

if [ -z "$LATEST_WEEK" ]; then
    echo "⚠️  No Week_* folders found on Beelink shareable."
    exit 1
fi

echo "📦 Downloading $LATEST_WEEK files..."
DEST="${MAC_ZWIFT_DIR}/${LATEST_WEEK}"
mkdir -p "${DEST}"

# Get individual file list from container source path (Python avoids Windows cmd quoting pitfalls)
FILES=$(ssh $SSH_OPTS ${BEELINK_USER}@${BEELINK_IP} \
  "docker exec ${SOURCE_CONTAINER} python3 -c \"import glob,os; p='/app/shareable/zwift_workouts/${LATEST_WEEK}/*.zwo'; files=sorted(glob.glob(p)); [print(os.path.basename(f)) for f in files]\"" \
  | tr -d '\r')

if [ -z "$FILES" ]; then
  echo "⚠️  No .zwo files found in ${LATEST_WEEK} in container volume."
    exit 1
fi

COUNT=0
for f in $FILES; do
  # Pull directly from the running container to avoid stale host-path copies
  ssh $SSH_OPTS ${BEELINK_USER}@${BEELINK_IP} \
    "docker exec ${SOURCE_CONTAINER} cat /app/shareable/zwift_workouts/${LATEST_WEEK}/${f}" > "${DEST}/${f}"
    COUNT=$((COUNT + 1))
done
echo "✅ Sync complete! Copied ${COUNT} workout(s) to ${DEST}"
