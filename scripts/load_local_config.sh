#!/bin/bash
# Sourced by deploy_to_beelink.sh, sync_db_from_beelink.sh and sync_zwift_from_beelink.sh.
#
# Machine-specific values (the server's address, user and folders, your Zwift folder) are NOT kept in git.
# They live in deploy.local.env, which is git-ignored. Start from deploy.local.env.example.

_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_ENV="${DEPLOY_LOCAL_ENV:-$_root/deploy.local.env}"

if [[ ! -f "$LOCAL_ENV" ]]; then
  echo "❌ $LOCAL_ENV not found."
  echo "   Copy deploy.local.env.example to deploy.local.env and fill in your server's details."
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$LOCAL_ENV"
set +a

: "${BEELINK_HOST:?set BEELINK_HOST in deploy.local.env}"
: "${BEELINK_USER:?set BEELINK_USER in deploy.local.env}"
: "${BEELINK_HOME:?set BEELINK_HOME in deploy.local.env}"

BEELINK="${BEELINK_USER}@${BEELINK_HOST}"
BEELINK_HOME_BS="${BEELINK_HOME//\//\\}"          # same folder with backslashes, for cmd.exe
REMOTE_DIR_FWD="${BEELINK_HOME}/fitness_tracker"
REMOTE_DIR="${BEELINK_HOME_BS}\\fitness_tracker"
