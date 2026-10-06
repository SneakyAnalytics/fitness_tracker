# Beelink runbook

The app runs on the Beelink (Windows + Docker Desktop/WSL2), reached over Tailscale.

| What | URL (Tailscale) |
|---|---|
| Training app (calendar, coaching, dashboard) | http://100.117.194.8:3000 |
| Admin (import, workout matching, analysis) | http://100.117.194.8:8501 |
| API health | http://100.117.194.8:8000/health |

## How code gets there

1. Merge to `main` and push.
2. GitHub Actions (`.github/workflows/docker.yml`) runs the tests, then builds two
   images and pushes them to GitHub Container Registry, tagged `:main` and `:<commit sha>`:
   - `ghcr.io/sneakyanalytics/fitness-tracker` (API + Streamlit)
   - `ghcr.io/sneakyanalytics/fitness-tracker-web` (React app behind nginx)
3. From the Mac: `./deploy_to_beelink.sh`. It checks Docker and the images, **backs up the
   database** (newest 10 kept in `/app/data/backups/`), copies `docker-compose.yml`,
   pulls, restarts and waits for `/health`.

The Beelink builds nothing and runs no source tree. It needs only
`C:\Users\rakej\fitness_tracker\docker-compose.yml`, `.env`, and the three Docker volumes
(`fitness_tracker_data`, `_logs`, `_shareable`), which hold the database, logs and Zwift files.

**Never** copy `.py` files into the data volume or `docker cp` code into containers as a
deploy method. It is lost on the next pull, and before October 2026 it made production
silently diverge from git.

## Common tasks

```bash
./deploy_to_beelink.sh                                # deploy what origin/main points at
./deploy_to_beelink.sh --version <sha>                # roll back / pin a specific commit
./deploy_to_beelink.sh --env TRAININGPEAKS_PASSWORD   # also push one key from the Mac .env
./sync_db_from_beelink.sh                             # copy the live DB to the Mac for testing
```

The Beelink `.env` has keys the Mac's doesn't (Zwift-to-Mac sync, email, news), so it
is never overwritten wholesale. `--env KEY` merges only the named keys. Values containing
`$` must be single-quoted (`KEY='va$lue'`) because Compose expands `$`; the script does this.

On the Beelink (PowerShell, in `C:\Users\rakej\fitness_tracker`):

```powershell
docker compose ps                                     # status + health
docker compose logs --tail 100 fastapi                # API logs
docker compose up -d                                  # start everything (pinned APP_VERSION in .env)
docker exec fitness-tracker-api python -m src.utils.maintenance --help
```

Restore a backup: stop the stack (`docker compose stop`), then
`docker run --rm -v fitness_tracker_data:/d alpine cp /d/backups/<file>.db /d/fitness_data.db`,
then `docker compose up -d`.

## Keeping Docker stable on Windows

Already in place: Docker Desktop auto-start tasks, `restart: unless-stopped`, health checks
(Streamlit and the web app wait for a healthy API), container log rotation (10 MB × 3),
image pruning after each deploy, sleep disabled, and the network watchdog task.

Recommended WSL settings (`C:\Users\rakej\.wslconfig`). The machine has 20 GB RAM and 16
cores; a 2 GB cap leaves Docker very little headroom once Chromium runs a TrainingPeaks sync:

```ini
[wsl2]
memory=6GB
processors=4
swap=4GB
vmIdleTimeout=60000

[experimental]
autoMemoryReclaim=gradual   # returns idle memory to Windows (the original vmmem problem)
```

Apply with `wsl --shutdown` (Docker Desktop restarts; the containers come back on their own).

If the stack is down: start Docker Desktop, wait for it to say "running", then
`docker compose up -d`. Check `GET /health`. The Streamlit sidebar shows any recorded
background failures (nightly sync, analysis) under "problem(s) need attention".
