# Documentation

Start with the [project README](../README.md): what the system does, the sports science behind it and the architecture.

| Read | For |
|---|---|
| [`deployment/RUNBOOK.md`](deployment/RUNBOOK.md) | **Current.** How code reaches the server, rollback, scheduled tasks and Docker/WSL stability |
| [`../AGENTS.md`](../AGENTS.md) | **Current.** Post-mortems of past bugs and the rules they produced |
| [`deployment/local-development.md`](deployment/local-development.md) | Running the API, admin app and front end on a laptop |
| [`deployment/beelink-setup.md`](deployment/beelink-setup.md), [`docker-guide.md`](deployment/docker-guide.md) | First-time server setup and Docker notes |
| [`architecture/`](architecture) | Original design notes: database schema, data flow, API endpoints, the coaching system |
| [`features/`](features) | Original per-feature notes: TrainingPeaks sync, workout analysis, AI coaching |

The architecture and feature notes were written for the first, Streamlit-based version and carry a status line saying so.
The app has since grown (computed training load, measured execution scoring, a tool-using coach, a React front end);
the README and the runbook reflect that.

Machine-specific details (server address, usernames, folders) are deliberately not in this repository.
They live in git-ignored files: copy [`deploy.local.env.example`](../deploy.local.env.example) to `deploy.local.env`.
