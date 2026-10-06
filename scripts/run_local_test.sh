#!/bin/bash
# Run the whole app on the Mac against a COPY of the live data, for testing.
#
#   ./scripts/run_local_test.sh          # fresh copy from the Beelink, then start
#   ./scripts/run_local_test.sh --reuse  # reuse the last copy
#
# Open http://localhost:3000 (or http://<mac tailscale ip>:3000 from your phone).
# Coach/ask calls use your real API keys (cents per call). Saves go to the copy,
# and Zwift files to /tmp, never your real Zwift folder. Ctrl-C stops everything.
set -euo pipefail
cd "$(dirname "$0")/.."
TEST_DB=/tmp/fitness_test/fitness_data.db
mkdir -p /tmp/fitness_test/zwift

if [[ "${1:-}" != "--reuse" || ! -f "$TEST_DB" ]]; then
  ./sync_db_from_beelink.sh
  cp data/fitness_data.db "$TEST_DB"
  FITNESS_DB_PATH="$TEST_DB" .venv/bin/python -m src.utils.maintenance backfill
fi

export FITNESS_DB_PATH="$TEST_DB" ZWIFT_WORKOUTS_DIR=/tmp/fitness_test/zwift
trap 'kill 0' EXIT
.venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port 8000 &
.venv/bin/streamlit run src/ui/streamlit_app.py --server.port 8501 --server.headless true &
(cd frontend && npx vite --port 3000 --host) &
wait
