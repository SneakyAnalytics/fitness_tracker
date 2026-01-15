# AI Agent Instructions Hub

Welcome, AI Agent! This guide will help you understand the Fitness Tracker application and work effectively as a development assistant.

## Quick Start

1. **Read this first**: [Getting Started Guide](./getting-started.md)
2. **Understand the architecture**: [Architecture Overview](../architecture/overview.md)
3. **Learn the database**: [Database Schema](../architecture/database-schema.md)
4. **Review development standards**: [Development Workflow](./development-workflow.md)

## Core Principles

### When Making Changes

✅ **DO:**

- Always test changes locally before deploying
- Update relevant documentation when modifying code
- Follow existing code patterns and conventions
- Use password-less SSH when accessing the Beelink
- Check for breaking changes in database queries
- Run the app in Docker to match production environment

❌ **DON'T:**

- Make changes without understanding the full data flow
- Modify database schema without migration scripts
- Hardcode paths - use environment variables
- Skip testing after file reorganization
- Assume Windows paths work like Unix paths

### Documentation Standards

When you modify the application:

1. Update the relevant docs in `docs/` folder
2. If adding a new feature, document it in `docs/features/`
3. If changing architecture, update `docs/architecture/`
4. Keep `docs/agent-instructions/` up to date with new patterns

### Testing Workflow

```bash
# Test locally on Mac
docker compose down && docker compose up -d

# Verify containers are healthy
docker ps

# Test API
curl http://localhost:8000/health

# Test UI
open http://localhost:8501

# After verification, sync to Beelink
./sync_to_beelink.sh 100.117.194.8  # via Tailscale
# OR
./sync_to_beelink.sh 192.168.1.29   # via local network

# On Beelink, restart containers
ssh rakej@100.117.194.8 "cd C:\Users\rakej\fitness_tracker && docker compose restart"
```

## Application Overview

### Purpose

Personal fitness tracking and AI-powered coaching application that:

- Syncs workouts from TrainingPeaks
- Analyzes FIT files from cycling workouts
- Detects intervals and calculates power metrics
- Provides AI-generated weekly training plans
- Generates Zwift workout files (.zwo)

### Technology Stack

- **Backend**: FastAPI (Python 3.12)
- **Frontend**: Streamlit
- **Database**: SQLite
- **Deployment**: Docker Compose
- **Hosting**: Beelink SER5 Max (Windows 11) running 24/7
- **Access**: Tailscale mesh VPN

### Key Components

1. **TrainingPeaks Sync** (`src/utils/trainingpeaks_automation.py`)
2. **FIT File Parser** (`src/utils/fit_parser.py`)
3. **Interval Detection** (`src/utils/interval_detector.py`)
4. **AI Coach** (`src/utils/ai_coach_engine.py`)
5. **Zwift Generator** (`src/utils/zwift_workout_generator.py`)
6. **Database Layer** (`src/storage/database.py`)
7. **Streamlit UI** (`src/ui/streamlit_app.py`)

## Repository Structure

```
fitness_tracker/
├── src/                          # Application source code
│   ├── api/                      # FastAPI backend
│   ├── models/                   # Data models
│   ├── storage/                  # Database layer
│   ├── ui/                       # Streamlit frontend
│   └── utils/                    # Utility modules
├── docs/                         # Documentation (you are here)
│   ├── agent-instructions/       # AI agent guides
│   ├── architecture/             # System architecture
│   ├── deployment/               # Deployment guides
│   ├── features/                 # Feature documentation
│   └── history/                  # Historical docs
├── data/                         # SQLite database and files
├── tests/                        # Test files
├── scripts/                      # Utility scripts
├── migrations/                   # Database migrations
├── docker-compose.yml            # Container orchestration
└── requirements.txt              # Python dependencies
```

## Quick Links

- [Getting Started](./getting-started.md)
- [Database Schema](../architecture/database-schema.md)
- [Streamlit App Structure](../architecture/streamlit-app.md)
- [Development Workflow](./development-workflow.md)
- [Testing Guide](./testing-guide.md)
- [Beelink Access](../deployment/beelink-setup.md)
- [Troubleshooting](../deployment/troubleshooting.md)

## Common Tasks

### Adding a New Feature

1. Understand the data flow (see [Architecture](../architecture/overview.md))
2. Implement in appropriate module (`src/utils/`, `src/api/`, etc.)
3. Add UI components if needed (`src/ui/streamlit_app.py`)
4. Update database schema if needed (create migration)
5. Test locally with Docker
6. Document in `docs/features/`
7. Deploy to Beelink

### Debugging Issues

1. Check container logs: `docker logs fitness-tracker-ui`
2. Verify database: `sqlite3 data/fitness_data.db`
3. Review recent changes in git history
4. Check environment variables in `.env`
5. See [Troubleshooting Guide](../deployment/troubleshooting.md)

### Accessing the Beelink

```bash
# Via Tailscale (works anywhere)
ssh rakej@100.117.194.8

# Via local network (same WiFi only)
ssh rakej@192.168.1.29

# Password-less auth is configured
# Tailscale IP: 100.117.194.8
# Local IP: 192.168.1.29
```

## Environment Details

### Production (Beelink)

- **OS**: Windows 11
- **Location**: Living room, running 24/7
- **User**: rakej
- **Path**: `C:\Users\rakej\fitness_tracker\`
- **Access**:
  - Web UI: http://100.117.194.8:8501
  - SSH: `ssh rakej@100.117.194.8`
  - Docker: Running in WSL2

### Development (Mac)

- **User**: jacobrobinson
- **Path**: `/Users/jacobrobinson/fitness_tracker/`
- **Python**: 3.12.0 (venv)
- **Docker**: Docker Desktop for Mac

## Support

For questions about specific components, see the detailed documentation in:

- [Architecture docs](../architecture/)
- [Feature docs](../features/)
- [Deployment docs](../deployment/)
