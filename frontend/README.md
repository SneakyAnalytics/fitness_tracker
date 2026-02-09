# Pacific Northwest Fitness Tracker - React Frontend

Modern React-based frontend for the fitness tracker application, featuring a Pacific Northwest-inspired design theme.

## 🎨 Design Philosophy

The UI is inspired by the natural beauty of the Pacific Northwest:

- **Forest Green** (#2C5F2D): Primary actions, navigation highlights
- **Mountain Blue** (#4A7C7E): Secondary elements, complementary accents
- **Gravel Tan** (#B8956A): Warm accents, highlighting
- **Soft Cream** (#F5F5F0): Backgrounds, surfaces

Clean, modern interface optimized for readability of workout routines and training data.

## 🏗️ Architecture

### Technology Stack

- **React 19** - UI framework
- **Vite 7** - Build tool and dev server
- **React Router 7** - Client-side routing
- **Axios** - HTTP client for FastAPI integration
- **Recharts** - Data visualization
- **Lucide React** - Icon library
- **date-fns** - Date manipulation

### Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.js          # FastAPI client wrapper
│   ├── components/
│   │   ├── AppLayout.jsx      # Main layout with sidebar
│   │   └── UserProfile.jsx    # Athlete settings dropdown
│   ├── pages/
│   │   ├── WorkoutCalendar.jsx    # Weekly calendar view
│   │   ├── WorkoutImport.jsx      # TrainingPeaks sync
│   │   ├── WeeklyCoaching.jsx     # AI coaching workflow
│   │   └── Dashboard.jsx          # Analytics & progress
│   ├── styles/
│   │   ├── index.css          # Global styles & theme
│   │   ├── App.css            # Component styles
│   │   └── pages.css          # Page-specific styles
│   ├── App.jsx                # Main app component
│   └── main.jsx               # React entry point
├── index.html
├── vite.config.js
└── package.json
```

## 🚀 Development

### Prerequisites

- Node.js 20.19+ or 22.12+ (currently using 22.3.0 with warnings)
- npm 10+
- FastAPI backend running on `localhost:8000`

### Getting Started

1. **Install dependencies:**

   ```bash
   cd frontend
   npm install
   ```

2. **Start development server:**

   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`

3. **Build for production:**

   ```bash
   npm run build
   ```

   Output will be in `frontend/dist/`

### Development with Backend

The Vite dev server is configured to proxy API requests to the FastAPI backend:

- **Development:** `http://localhost:3000` → forwards `/api/*` to `http://localhost:8000`
- **Production:** Set `VITE_API_URL` environment variable

**Start both services:**

```bash
# Terminal 1: Start FastAPI backend
cd /path/to/fitness_tracker
docker-compose up fastapi

# Terminal 2: Start React frontend
cd /path/to/fitness_tracker/frontend
npm run dev
```

## 📋 Features (In Progress)

### ✅ Completed

- [x] Project setup with Vite + React
- [x] PNW-themed design system
- [x] AppLayout with collapsible sidebar
- [x] API client for FastAPI integration
- [x] User profile with athlete settings
- [x] Routing structure

### 🚧 In Development

- [ ] **Workout Calendar** - Weekly view with routine/cardio workouts
- [ ] **Timer Component** - Functional work/rest timer
- [ ] **Interval Visualizer** - Graphical workout structure display
- [ ] **Workout Import** - TrainingPeaks sync and matching workflow
- [ ] **Weekly Coaching** - AI analysis and workout generation
- [ ] **Analytics Dashboard** - Consolidated progress tracking

## 🎯 Core Workflows

### 1. Workout Calendar (Primary Interface)

- Weekly calendar grid navigation
- View planned vs completed workouts
- **Routine workouts:** Exercise list with rep/weight tracking, clickable exercise images
- **Cardio workouts:** Summary info + interval visualization
- Embedded timer for timed workouts

### 2. Workout Import & Analysis

- TrainingPeaks sync with date range selection
- Manual workout matching (proposed ↔ completed)
- Re-match existing workouts
- FIT file assignment management

### 3. Weekly Review & Planning

- Select completed training week (Mon-Sun)
- Input: schedule constraints, goals, feedback, soreness
- AI workflow: Analyze week → Generate next week's plan
- Auto-generate Zwift .zwo files
- Cost tracking for AI API calls

### 4. Analytics Dashboard (Consolidated)

- **Daily View:** Workout timeline with AI analysis
- **Progress Overview:** TSS trends, training hours, distribution
- **Personal Bests:** Medal tracking (30s, 1min, 5min, etc.)
- **Goals & Patterns:** Coaching insights

## 🔌 API Integration

All API calls use the centralized client in `src/api/client.js`.

### Available API Methods:

```javascript
import { workoutAPI, athleteAPI, summaryAPI } from "./api/client";

// Workouts
await workoutAPI.getWeek(startDate, endDate);
await workoutAPI.saveQualitative(data);

// Athlete settings
await athleteAPI.getSettings();
await athleteAPI.saveSettings(data);

// Weekly summaries
await summaryAPI.generate(startDate, endDate);
```

See `src/api/client.js` for complete API documentation.

## 🎨 Styling Guide

### Theme Variables

```css
/* Colors */
--color-forest: #2c5f2d;
--color-mountain: #4a7c7e;
--color-gravel: #b8956a;
--color-cream: #f5f5f0;

/* Spacing */
--spacing-sm: 0.5rem;
--spacing-md: 1rem;
--spacing-lg: 1.5rem;
--spacing-xl: 2rem;

/* Border Radius */
--radius-md: 8px;
--radius-lg: 12px;
```

### Utility Classes

```html
<button class="btn btn-primary">Primary Action</button>
<div class="card">...</div>
<span class="badge badge-cycling">🚴 Cycling</span>
<div class="gradient-forest">...</div>
```

## 🧪 Testing

### Local Testing Checklist

- [ ] Calendar: View weeks, navigate, click days
- [ ] Routine Workout: Display exercises, enter reps/weight, save
- [ ] Timer: Start/stop, work/rest cycles, audio cues
- [ ] Import: Sync from TrainingPeaks, match workouts
- [ ] Coaching: Analyze week, generate plan, create Zwift files
- [ ] Dashboard: View charts, personal bests, goals
- [ ] Settings: Update FTP, zones, save successfully
- [ ] Responsive: Test on mobile/tablet layouts

## 📦 Deployment

### Option A: Serve from FastAPI

```python
# Add to src/api/app.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
```

### Option B: Separate Nginx Container

```yaml
# Add to docker-compose.yml
nginx:
  image: nginx:alpine
  ports:
    - "3000:80"
  volumes:
    - ./frontend/dist:/usr/share/nginx/html
```

## 🔒 Safety Features

- **Branch Isolation:** All work on `feature/react-frontend-migration`
- **No Production Impact:** Beelink production system untouched
- **Dual Operation:** Can run alongside Streamlit during development
- **Rollback Ready:** Keep Streamlit available until full feature parity

## 📝 Next Steps

1. **Build Workout Calendar** - Core UI with working timer
2. **Implement Import Workflow** - TrainingPeaks integration
3. **Create Weekly Coaching** - AI analysis + generation
4. **Consolidate Dashboard** - Unified analytics view
5. **Local Testing** - Validate all features
6. **Deployment Planning** - Prepare for Beelink migration

## 🤝 Contributing

This is a personal project in active development. Feature parity with the Streamlit version is the current goal before deployment to production Beelink system.

---

**Built with ❤️ for the Pacific Northwest outdoors**
