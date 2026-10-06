#!/bin/bash
# Sync fitness_data.db from Beelink to Mac for local testing
# This ensures you're testing with the current production data.
#
# The live DB lives inside the `fitness_tracker_data` Docker volume, NOT at the
# Windows host path, so we snapshot it from inside the running container using
# SQLite's backup API (consistent even while the app is writing).

set -e

BEELINK_IP="100.117.194.8"
BEELINK_USER="rakej"
BEELINK="${BEELINK_USER}@${BEELINK_IP}"
CONTAINER="fitness-tracker-api"
REMOTE_STAGING="C:/Users/rakej/ft_db_snapshot.db"
LOCAL_DB_PATH="./data/fitness_data.db"
BACKUP_PATH="./data/fitness_data.db.backup_$(date +%Y%m%d_%H%M%S)"
TMP_DB="$(mktemp -t fitness_snapshot).db"

echo "🔄 Syncing database from Beelink to Mac..."
echo "   Remote: ${CONTAINER}:/app/data/fitness_data.db on ${BEELINK}"
echo "   Local:  ${LOCAL_DB_PATH}"
echo ""

echo "🔌 Testing connection to Beelink..."
if ! ssh -o ConnectTimeout=5 "${BEELINK}" "echo Connected" &>/dev/null; then
    echo "❌ Cannot connect to Beelink. Check:"
    echo "   - Tailscale is running on both devices"
    echo "   - IP address is correct: ${BEELINK_IP}"
    echo "   - SSH is configured"
    exit 1
fi
echo "   ✓ Connected"

echo ""
echo "📸 Taking consistent snapshot inside the container..."
SNAP_SCRIPT="$(mktemp -t ft_snap).py"
cat > "${SNAP_SCRIPT}" <<'EOF'
import sqlite3
src = sqlite3.connect("/app/data/fitness_data.db")
dst = sqlite3.connect("/tmp/fitness_snapshot.db")
src.backup(dst)
dst.close()
src.close()
EOF
scp -q "${SNAP_SCRIPT}" "${BEELINK}:C:/Users/rakej/ft_snap.py"
ssh "${BEELINK}" "docker cp C:/Users/rakej/ft_snap.py ${CONTAINER}:/tmp/ft_snap.py"
ssh "${BEELINK}" "docker exec ${CONTAINER} python3 /tmp/ft_snap.py"
ssh "${BEELINK}" "docker cp ${CONTAINER}:/tmp/fitness_snapshot.db ${REMOTE_STAGING}"
rm -f "${SNAP_SCRIPT}"

echo "📥 Downloading snapshot..."
scp -q "${BEELINK}:${REMOTE_STAGING}" "${TMP_DB}"

if [ "$(sqlite3 "${TMP_DB}" 'pragma integrity_check;')" != "ok" ]; then
    echo "❌ Downloaded snapshot failed integrity check; local DB left untouched."
    rm -f "${TMP_DB}"
    exit 1
fi

if [ -f "${LOCAL_DB_PATH}" ]; then
    cp "${LOCAL_DB_PATH}" "${BACKUP_PATH}"
    echo "💾 Previous local DB saved: ${BACKUP_PATH}"
fi
mv "${TMP_DB}" "${LOCAL_DB_PATH}"

LOCAL_SIZE=$(ls -lh "${LOCAL_DB_PATH}" | awk '{print $5}')
LATEST_WEEK=$(sqlite3 "${LOCAL_DB_PATH}" 'select max(weekNumber) from weekly_plans;')
echo ""
echo "✅ Database sync successful!"
echo "   Local database size: ${LOCAL_SIZE}"
echo "   Latest plan week:    ${LATEST_WEEK}"
