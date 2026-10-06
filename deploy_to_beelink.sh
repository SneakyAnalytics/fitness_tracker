#!/bin/bash
# Deploy to the Beelink by pulling prebuilt images (built by GitHub Actions from main).
#
# The Beelink builds nothing: it only needs docker-compose.yml, .env and the
# images. Every deploy is pinned to an exact commit, so rolling back is just
# deploying an older commit.
#
# Usage:
#   ./deploy_to_beelink.sh                 # deploy the commit origin/main points at
#   ./deploy_to_beelink.sh --env TRAININGPEAKS_PASSWORD
#                                          # ...and copy just these keys from your Mac .env
#                                          # (the Beelink .env has extra keys; never overwrite it whole)
#   ./deploy_to_beelink.sh --version <sha> # deploy (or roll back to) a specific commit
#   ./deploy_to_beelink.sh --first-run     # first deploy of the Oct 2026 overhaul: also backfill + goals
#
# Run between training weeks: a broken deploy mid-week costs real workouts.

set -euo pipefail

BEELINK="rakej@100.117.194.8"
REMOTE_DIR='C:\Users\rakej\fitness_tracker'
REMOTE_DIR_FWD="C:/Users/rakej/fitness_tracker"
ENV_KEYS=()
VERSION=""
FIRST_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env) ENV_KEYS+=("$2"); shift 2 ;;
    --version) VERSION="$2"; shift 2 ;;
    --first-run) FIRST_RUN=true; shift ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
done

cd "$(dirname "$0")"
remote() { ssh -o ConnectTimeout=10 "$BEELINK" "$@"; }
# Docker Desktop's Windows credential store needs an interactive logon, so registry
# operations over SSH fail ("A specified logon session does not exist"). Over SSH we
# use a config whose credential helper answers "none stored" (fine for public images).
DOCKER_SSH='set PATH=C:\Users\rakej\.docker-ssh\bin;%PATH%&& set DOCKER_CONFIG=C:\Users\rakej\.docker-ssh&&'
setup_docker_ssh() {
  remote 'if not exist C:\Users\rakej\.docker-ssh\bin mkdir C:\Users\rakej\.docker-ssh\bin' >/dev/null
  scp -q scripts/deploy/docker-ssh/config.json "$BEELINK:C:/Users/rakej/.docker-ssh/config.json"
  scp -q scripts/deploy/docker-ssh/docker-credential-anon.cmd "$BEELINK:C:/Users/rakej/.docker-ssh/bin/docker-credential-anon.cmd"
}

echo "🔌 Checking the Beelink..."
remote "docker info --format {{.ServerVersion}}" >/dev/null || {
  echo "❌ Docker isn't responding on the Beelink. Start Docker Desktop (or run scripts/start_docker_and_containers.ps1) and retry."
  exit 1
}

if [[ -z "$VERSION" ]]; then
  git fetch -q origin main
  VERSION=$(git rev-parse origin/main)
fi
echo "📌 Deploying commit ${VERSION:0:12}  ($(git log -1 --format=%s "$VERSION" 2>/dev/null || echo 'unknown locally'))"

setup_docker_ssh
echo "🔎 Checking the images exist for that commit..."
for image in fitness-tracker fitness-tracker-web; do
  if ! remote "$DOCKER_SSH docker manifest inspect ghcr.io/sneakyanalytics/$image:$VERSION" >/dev/null 2>&1; then
    echo "❌ ghcr.io/sneakyanalytics/$image:$VERSION not found (or not accessible)."
    echo "   - Has the 'Build images' GitHub Action finished for this commit?"
    echo "   - Are the ghcr.io packages public? (GitHub → your profile → Packages → package settings)"
    exit 1
  fi
done

echo "💾 Backing up the live database..."
scp -q scripts/deploy/backup_db.py "$BEELINK:C:/Users/rakej/ft_backup_db.py"
remote "docker cp C:/Users/rakej/ft_backup_db.py fitness-tracker-api:/tmp/backup_db.py" \
  && remote "docker exec fitness-tracker-api python3 /tmp/backup_db.py" \
  || { echo "❌ Backup failed; not deploying."; exit 1; }

# Merge KEY=VALUE lines into the Beelink .env without touching its other keys.
merge_env() {
  local updates; updates=$(mktemp)
  cat > "$updates"
  scp -q scripts/deploy/merge_env.ps1 "$BEELINK:C:/Users/rakej/ft_merge_env.ps1"
  scp -q "$updates" "$BEELINK:C:/Users/rakej/ft_env_updates.txt"
  rm -f "$updates"
  remote "powershell -NoProfile -ExecutionPolicy Bypass -File C:/Users/rakej/ft_merge_env.ps1 -EnvFile $REMOTE_DIR_FWD/.env -Updates C:/Users/rakej/ft_env_updates.txt"
}

# Keep the pre-overhaul app runnable as a fallback (docker-compose.legacy.yml, port 8601).
if ! remote "docker image inspect fitness-tracker-legacy-ui:2026-10-05" >/dev/null 2>&1; then
  remote "docker tag fitness_tracker-streamlit:latest fitness-tracker-legacy-ui:2026-10-05 && docker tag fitness_tracker-fastapi:latest fitness-tracker-legacy-api:2026-10-05" \
    && echo "🏷️  Tagged the current images as the legacy fallback" \
    || echo "⚠️  Could not tag legacy images (already replaced?)"
fi

echo "📤 Sending compose files and host-side scripts..."
scp -q docker-compose.yml "$BEELINK:$REMOTE_DIR_FWD/docker-compose.yml"
scp -q docker-compose.legacy.yml "$BEELINK:$REMOTE_DIR_FWD/docker-compose.legacy.yml"
# The 05:00 ZwiftSyncToMac task runs this from the Beelink's disk.
scp -q scripts/beelink_sync_zwift_to_mac.ps1 "$BEELINK:$REMOTE_DIR_FWD/scripts/beelink_sync_zwift_to_mac.ps1"
if [[ ${#ENV_KEYS[@]} -gt 0 ]]; then
  for key in "${ENV_KEYS[@]}"; do
    grep -q "^$key=" .env || { echo "❌ $key not found in local .env"; exit 1; }
  done
  for key in "${ENV_KEYS[@]}"; do
    line=$(grep "^$key=" .env); val=${line#*=}
    # Compose expands $ in .env values; single-quote them so passwords survive intact.
    if [[ "$val" == *'$'* && "$val" != \'*\' ]]; then line="$key='$val'"; fi
    printf '%s\n' "$line"
  done | merge_env
fi
# Pin the version so a plain 'docker compose up -d' on the Beelink keeps it.
echo "APP_VERSION=$VERSION" | merge_env

echo "⬇️  Pulling images and restarting..."
remote "$DOCKER_SSH cd /d $REMOTE_DIR && docker compose pull && docker compose up -d --remove-orphans"

echo "🩺 Waiting for health..."
for i in $(seq 1 30); do
  if health=$(remote "curl -sf http://localhost:8000/health" 2>/dev/null); then
    echo "✅ $health"
    break
  fi
  sleep 10
  if [[ $i -eq 30 ]]; then
    echo "❌ API did not become healthy. Logs: ssh $BEELINK \"docker logs --tail 80 fitness-tracker-api\""
    echo "   Roll back: ./deploy_to_beelink.sh --version <previous sha>"
    exit 1
  fi
done
remote "docker ps --format \"{{.Names}}\t{{.Status}}\""
remote "docker image prune -f" >/dev/null

if $FIRST_RUN; then
  echo "🧹 One-time backfill (ride-file links, lap markers, execution scores, Zwift FTP)..."
  remote "docker exec fitness-tracker-api python -m src.utils.maintenance backfill"
  echo "🎯 Goals update..."
  remote "docker exec fitness-tracker-api python scripts/deploy/goals_2026_10.py"
fi

cat <<EOF

Deployed ${VERSION:0:12}.  Calendar & coaching: http://100.117.194.8:3000   Admin: http://100.117.194.8:8501

Old app (fallback), only if needed:
  ssh $BEELINK "cd /d $REMOTE_DIR && docker compose -f docker-compose.legacy.yml -p fitness-legacy up -d"
  then http://100.117.194.8:8601  (stop it again with ... down)
EOF
