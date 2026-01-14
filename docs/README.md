# Fitness Tracker Documentation Hub

Welcome to the fitness tracker documentation! This directory contains comprehensive guides for developers, AI agents, and contributors.

## 📚 Documentation Structure

```
docs/
├── agent-instructions/    # Start here for AI agents
│   ├── README.md         # AI Agent Instructions Hub
│   ├── getting-started.md
│   └── development-workflow.md
│
├── architecture/          # System design and technical details
│   ├── database-schema.md
│   ├── streamlit-app.md
│   ├── overview.md
│   └── data-flow.md
│
├── deployment/            # Setup and deployment guides
│   ├── beelink-setup.md
│   ├── docker-guide.md
│   ├── docker-setup-phase1.md
│   └── local-development.md
│
├── features/              # Feature-specific documentation
│   ├── ai-coaching.md
│   ├── trainingpeaks-sync.md
│   ├── workout-analysis.md
│   └── session-comparison.md
│
└── history/               # Historical documentation
    └── legacy-docs/       # Old planning and implementation docs
```

## 🤖 For AI Agents

**Start here:** [agent-instructions/README.md](./agent-instructions/README.md)

This is your primary entry point for understanding the application, development workflows, and coding standards.

**Quick Links:**

- [Getting Started Guide](./agent-instructions/getting-started.md) - First-time setup and code patterns
- [Development Workflow](./agent-instructions/development-workflow.md) - How to make changes and deploy
- [Database Schema](./architecture/database-schema.md) - Complete database documentation
- [Streamlit App](./architecture/streamlit-app.md) - 4,400-line UI breakdown

## 👥 For Human Developers

### New to the Project?

1. **Read the [Getting Started Guide](./agent-instructions/getting-started.md)**

   - Prerequisites and setup
   - Data flow diagrams
   - Common code patterns
   - Common gotchas

2. **Explore the Architecture**

   - [Database Schema](./architecture/database-schema.md) - Tables, relationships, query patterns
   - [API Endpoints](./architecture/api-endpoints.md) - FastAPI REST API reference (20+ endpoints)
   - [Streamlit App](./architecture/streamlit-app.md) - UI structure and components
   - ⭐ **[Data Processing Pipeline](./architecture/data-processing-pipeline.md)** - FIT parsing, interval detection, AI analysis
   - ⭐ **[AI Coaching System](./architecture/ai-coaching-system.md)** - RAG, orchestration, prompt engineering
   - ⭐ **[Automation & Sync](./architecture/automation-and-sync.md)** - TrainingPeaks sync, daily automation, scheduling
   - [System Overview](./architecture/overview.md) - High-level architecture
   - [Data Flow](./architecture/data-flow.md) - How data moves through the system

3. **Learn the Development Process**
   - [Development Workflow](./agent-instructions/development-workflow.md) - Git, testing, deployment
   - [Local Development](./deployment/local-development.md) - Run locally without Docker
   - [Docker Guide](./deployment/docker-guide.md) - Containerized deployment

### Ready to Contribute?

**Common Tasks:**

- **Adding API Endpoint**: See [development-workflow.md#adding-a-new-api-endpoint](./agent-instructions/development-workflow.md#adding-a-new-api-endpoint)
- **Adding UI Tab**: See [development-workflow.md#adding-a-new-streamlit-tab](./agent-instructions/development-workflow.md#adding-a-new-streamlit-tab)
- **Database Changes**: See [development-workflow.md#modifying-database-schema](./agent-instructions/development-workflow.md#modifying-database-schema)
- **New Utility Function**: See [development-workflow.md#adding-a-new-utility-function](./agent-instructions/development-workflow.md#adding-a-new-utility-function)

## 🎯 Documentation by Topic

### Features

- [AI Coaching](./features/ai-coaching.md) - AI-powered weekly plan generation
- [TrainingPeaks Sync](./features/trainingpeaks-sync.md) - Automated workout import
- [Workout Analysis](./features/workout-analysis.md) - FIT file parsing and interval detection
- [Session Comparison](./features/session-comparison.md) - Compare workouts side-by-side

### Deployment

- [Beelink Setup](./deployment/beelink-setup.md) - Production server configuration
- [Docker Guide](./deployment/docker-guide.md) - Container deployment
- [Local Development](./deployment/local-development.md) - Run without Docker

### Architecture

- [Database Schema](./architecture/database-schema.md) - Complete DB documentation
- [API Endpoints](./architecture/api-endpoints.md) - FastAPI REST API (20+ endpoints)
- [Streamlit App](./architecture/streamlit-app.md) - 4,400-line UI breakdown
- ⭐ **[Data Processing Pipeline](./architecture/data-processing-pipeline.md)** - FIT parsing, intervals, AI analysis
- ⭐ **[AI Coaching System](./architecture/ai-coaching-system.md)** - RAG, orchestration, prompts
- ⭐ **[Automation & Sync](./architecture/automation-and-sync.md)** - TrainingPeaks sync, daily automation, scheduling
- [System Overview](./architecture/overview.md) - High-level architecture
- [Data Flow](./architecture/data-flow.md) - Data movement through system
- [Streamlit App](./architecture/streamlit-app.md) - UI architecture (4,400 lines)
- [System Overview](./architecture/overview.md) - High-level design
- [Data Flow](./architecture/data-flow.md) - Data movement patterns

## 📝 Documentation Standards

When updating documentation:

1. **Update docs/ when modifying code**

   - New features → `docs/features/`
   - Architecture changes → `docs/architecture/`
   - Deployment changes → `docs/deployment/`

2. **Keep agent-instructions/ current**

   - These are the primary onboarding docs for AI agents
   - Update when workflows or patterns change

3. **Include code examples**

   - Show both ✅ DO and ❌ DON'T patterns
   - Provide working code snippets
   - Link to relevant source files

4. **Cross-reference related docs**
   - Link to related documentation
   - Keep navigation easy

## 🔧 Tools and Technologies

**Core Stack:**

- **Backend:** FastAPI (Python 3.12)
- **Frontend:** Streamlit
- **Database:** SQLite
- **Deployment:** Docker Compose
- **Network:** Tailscale mesh VPN
- **AI:** Claude 3.5 Sonnet, Gemini 1.5 Flash

**Key Libraries:**

- `fitparse` - FIT file parsing
- `playwright` - TrainingPeaks automation
- `plotly` - Interactive charts
- `pandas` - Data manipulation
- `requests` - API communication

## 🚀 Quick Start

```bash
# Clone and setup
cd /Users/jacobrobinson/fitness_tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Edit with your API keys

# Start with Docker
docker compose up -d

# Access application
# API: http://localhost:8000
# UI: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

## 📞 Support

- **Documentation Issues:** Update the relevant file in `docs/`
- **Code Issues:** Follow [development-workflow.md](./agent-instructions/development-workflow.md#debugging-workflow)
- **Deployment Issues:** Check [deployment/](./deployment/) guides

## 🗂️ Legacy Documentation

Historical documentation is preserved in [history/legacy-docs/](./history/legacy-docs/). These files document past features, implementation plans, and completed phases. They're kept for reference but may not reflect the current state of the application.

## 📈 Documentation Roadmap

**Completed:**

- ✅ AI Agent Instructions Hub
- ✅ Database Schema Documentation
- ✅ Streamlit App Architecture
- ✅ Development Workflow Guide
- ✅ Getting Started Guide

**Future Additions:**

- ⏳ API Endpoints Reference
- ⏳ Testing Guide
- ⏳ Contribution Standards
- ⏳ Troubleshooting Guide
- ⏳ Performance Optimization Guide

---

**Last Updated:** January 2026  
**Maintained By:** Jacob Robinson + AI Agents
